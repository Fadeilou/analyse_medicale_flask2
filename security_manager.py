"""
Module de sécurité avancée
Gère l'authentification à deux facteurs (2FA) et le chiffrement des données sensibles
"""
import pyotp
import qrcode
from io import BytesIO
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import secrets
import os
from flask import current_app
from models import db


class SecurityManager:
    """Gestionnaire principal de la sécurité"""
    
    def __init__(self):
        self.encryption_key = self._get_or_create_encryption_key()
        self.fernet = Fernet(self.encryption_key)
    
    def _get_or_create_encryption_key(self):
        """Récupère ou crée une clé de chiffrement"""
        # En production, stocker cette clé de manière sécurisée (ex: AWS KMS, HashiCorp Vault)
        key_file = 'instance/encryption.key'
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            os.makedirs('instance', exist_ok=True)
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    def encrypt_data(self, data):
        """Chiffre des données sensibles"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return self.fernet.encrypt(data).decode('utf-8')
    
    def decrypt_data(self, encrypted_data):
        """Déchiffre des données"""
        if isinstance(encrypted_data, str):
            encrypted_data = encrypted_data.encode('utf-8')
        return self.fernet.decrypt(encrypted_data).decode('utf-8')
    
    def hash_sensitive_data(self, data, salt=None):
        """Hash des données avec salt pour stockage sécurisé"""
        if salt is None:
            salt = os.urandom(32)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(data.encode('utf-8')))
        return base64.urlsafe_b64encode(salt + key).decode('utf-8')


class TwoFactorAuth:
    """Gestionnaire de l'authentification à deux facteurs"""
    
    @staticmethod
    def generate_secret():
        """Génère un secret pour 2FA"""
        return pyotp.random_base32()
    
    @staticmethod
    def generate_qr_code(user_email, secret, issuer="Analyse Médicale"):
        """Génère un QR code pour l'application d'authentification"""
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user_email,
            issuer_name=issuer
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convertir en base64 pour l'affichage web
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{qr_code_base64}"
    
    @staticmethod
    def verify_token(secret, token):
        """Vérifie un token 2FA"""
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(token, valid_window=1)  # Fenêtre de 1 période (30s) de tolérance
        except:
            return False
    
    @staticmethod
    def generate_backup_codes(count=10):
        """Génère des codes de sauvegarde pour 2FA"""
        return [secrets.token_hex(4).upper() for _ in range(count)]


def add_2fa_fields_to_user_model():
    """Ajoute les champs 2FA au modèle User (migration)"""
    # Cette fonction serait utilisée dans une migration Alembic
    # Voici le SQL équivalent :
    sql_commands = [
        "ALTER TABLE user ADD COLUMN two_factor_enabled BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE user ADD COLUMN two_factor_secret VARCHAR(32);",
        "ALTER TABLE user ADD COLUMN backup_codes TEXT;",  # JSON string des codes de sauvegarde
        "ALTER TABLE user ADD COLUMN last_2fa_use TIMESTAMP;"
    ]
    return sql_commands


class DataProtection:
    """Classe pour la protection des données sensibles selon RGPD/HIPAA"""
    
    def __init__(self):
        self.security_manager = SecurityManager()
    
    def anonymize_patient_data(self, patient_id):
        """Anonymise les données d'un patient (pour conformité RGPD)"""
        from models import Patient, AnalyseResult
        
        try:
            patient = Patient.query.get(patient_id)
            if not patient:
                return False
            
            # Sauvegarder les données originales si nécessaire (audit)
            original_data = {
                'nom': patient.nom,
                'prenom': patient.prenom,
                'email': patient.email,
                'telephone': patient.telephone,
                'adresse': patient.adresse
            }
            
            # Anonymiser
            anonymous_id = f"PATIENT_ANONYME_{patient_id}_{secrets.token_hex(4)}"
            patient.nom = anonymous_id
            patient.prenom = "ANONYME"
            patient.email = f"anonyme_{patient_id}@deleted.local"
            patient.telephone = "SUPPRIME"
            patient.adresse = "ADRESSE SUPPRIMEE"
            
            # Marquer les analyses comme anonymisées
            for analyse in patient.analyses:
                analyse.statut = "ANONYMISE"
            
            db.session.commit()
            
            # Log de l'anonymisation
            from auth_decorators import audit_action
            audit_action(
                action="ANONYMIZE",
                resource_type="Patient",
                resource_id=patient_id,
                details={"original_data_hash": self.security_manager.hash_sensitive_data(str(original_data))}
            )
            
            return True
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erreur lors de l'anonymisation du patient {patient_id}: {e}")
            return False
    
    def export_patient_data(self, patient_id):
        """Export des données patient (droit à la portabilité RGPD)"""
        from models import Patient, AnalyseResult
        
        try:
            patient = Patient.query.get(patient_id)
            if not patient:
                return None
            
            # Données patient
            patient_data = {
                'informations_personnelles': {
                    'nom': patient.nom,
                    'prenom': patient.prenom,
                    'date_naissance': patient.date_naissance.isoformat() if patient.date_naissance else None,
                    'sexe': patient.sexe,
                    'telephone': patient.telephone,
                    'email': patient.email,
                    'adresse': patient.adresse
                },
                'informations_medicales': {
                    'antecedents_medicaux': patient.antecedents_medicaux,
                    'allergies': patient.allergies,
                    'medecin_traitant': patient.medecin_traitant
                },
                'analyses': []
            }
            
            # Analyses du patient
            for analyse in patient.analyses:
                analyse_data = {
                    'id': analyse.id,
                    'date_analyse': analyse.date_analyse.isoformat(),
                    'test_positif': analyse.test_positif,
                    'type_anomalie': analyse.type_anomalie,
                    'recommandation': analyse.recommandation,
                    'commentaire_medecin': analyse.commentaire_medecin,
                    'statut': analyse.statut
                }
                patient_data['analyses'].append(analyse_data)
            
            return patient_data
        except Exception as e:
            current_app.logger.error(f"Erreur lors de l'export des données du patient {patient_id}: {e}")
            return None


class SessionSecurity:
    """Gestion sécurisée des sessions"""
    
    @staticmethod
    def generate_csrf_token():
        """Génère un token CSRF"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def validate_session_security(request, user):
        """Valide la sécurité de la session"""
        # Vérifier l'IP (optionnel, peut poser problème avec les proxies)
        # Vérifier le User-Agent pour détecter les changements suspects
        # Vérifier la validité temporelle de la session
        
        session_checks = {
            'ip_consistent': True,  # À implémenter selon les besoins
            'user_agent_consistent': True,  # À implémenter
            'session_valid': True
        }
        
        return all(session_checks.values())
    
    @staticmethod
    def log_security_event(event_type, user_id, details):
        """Log les événements de sécurité"""
        from models import AuditLog
        
        security_log = AuditLog(
            user_id=user_id,
            action=f"SECURITY_{event_type}",
            resource_type="Session",
            details=details,
            ip_address=details.get('ip_address'),
            user_agent=details.get('user_agent')
        )
        
        db.session.add(security_log)
        db.session.commit()


# Instance globale du gestionnaire de sécurité
security_manager = SecurityManager()
two_factor_auth = TwoFactorAuth()
data_protection = DataProtection()
session_security = SessionSecurity()
