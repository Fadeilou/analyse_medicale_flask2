#!/usr/bin/env python3
"""
Script pour réinitialiser complètement la base de données
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Patient, AnalyseResult, RoleEnum, Notification, AuditLog, Annotation
from werkzeug.security import generate_password_hash
from datetime import datetime, date, timezone
import traceback

def utcnow():
    """Timezone-aware UTC now function"""
    return datetime.now(timezone.utc)

def force_reset_database():
    """Force la réinitialisation complète de la base de données"""
    with app.app_context():
        try:
            print("🔄 Suppression forcée des tables...")
            db.drop_all()
            print("✅ Tables supprimées!")
            
            print("🔄 Création des nouvelles tables...")
            db.create_all()
            print("✅ Nouvelles tables créées!")
            
            print("🔄 Création des utilisateurs par défaut...")
            
            # Créer un administrateur par défaut
            admin = User(
                username='admin',
                email='admin@medicale.com',
                password=generate_password_hash('admin123'),
                role=RoleEnum.ADMINISTRATEUR,
                is_active=True,
                created_at=utcnow()
            )
            db.session.add(admin)
            
            # Créer un médecin par défaut
            medecin = User(
                username='dr_martin',
                email='medecin@medicale.com',
                password=generate_password_hash('medecin123'),
                role=RoleEnum.MEDECIN,
                is_active=True,
                created_at=utcnow()
            )
            db.session.add(medecin)
            
            # Créer quelques patients de test
            patient1 = Patient(
                nom='Dupont',
                prenom='Jean',
                date_naissance=date(1980, 5, 15),
                sexe='M',
                telephone='0123456789',
                email='jean.dupont@email.com',
                adresse='123 Rue de la Santé, 75000 Paris',
                antecedents_medicaux='Hypertension artérielle',
                allergies='Pénicilline',
                medecin_traitant='Dr. Smith',
                created_at=utcnow()
            )
            
            patient2 = Patient(
                nom='Martin',
                prenom='Marie',
                date_naissance=date(1990, 8, 22),
                sexe='F',
                telephone='0987654321',
                email='marie.martin@email.com',
                adresse='456 Avenue de la Paix, 69000 Lyon',
                antecedents_medicaux='Diabète type 2',
                allergies='Aucune',
                medecin_traitant='Dr. Johnson',
                created_at=utcnow()
            )
            
            db.session.add(patient1)
            db.session.add(patient2)
            
            # Créer un utilisateur patient lié à patient1
            user_patient = User(
                username='jean_dupont',
                email='jean.dupont@email.com',
                password=generate_password_hash('patient123'),
                role=RoleEnum.PATIENT,
                is_active=True,
                created_at=utcnow()
            )
            db.session.add(user_patient)
            
            # Sauvegarder tous les utilisateurs et patients
            db.session.commit()
            
            # Lier le patient1 au user_patient
            user_patient.patient_id = patient1.id
            db.session.commit()
            
            # Créer une notification de bienvenue pour l'admin
            notification = Notification(
                user_id=admin.id,
                titre='Bienvenue sur la plateforme d\'analyse médicale',
                message='Votre système d\'analyse médicale est maintenant opérationnel. Vous pouvez commencer à gérer les utilisateurs et superviser les analyses.',
                type_notification='SYSTEME',
                lu=False,
                created_at=utcnow()
            )
            db.session.add(notification)
            
            db.session.commit()
            
            print("✅ Base de données réinitialisée avec succès!")
            print("\n📋 Comptes créés:")
            print("👤 Admin: admin / admin123")
            print("🩺 Médecin: dr_martin / medecin123")
            print("🧑‍⚕️ Patient: jean_dupont / patient123")
            print("\n🌟 Nouvelles fonctionnalités disponibles:")
            print("- Gestion complète des patients")
            print("- Système de notifications")
            print("- Statistiques et tableau de bord")
            print("- Export PDF des rapports")
            print("- Interface d'administration")
            print("- Monitoring système")
            
        except Exception as e:
            print(f"❌ Erreur lors de la réinitialisation: {e}")
            print(traceback.format_exc())
            db.session.rollback()

if __name__ == '__main__':
    force_reset_database()
