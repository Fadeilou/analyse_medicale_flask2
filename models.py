from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone
import enum

db = SQLAlchemy() # Instance SQLAlchemy pour toute l'application

def utcnow():
    """Timezone-aware UTC now function"""
    return datetime.now(timezone.utc)

class RoleEnum(enum.Enum):
    PATIENT = "patient"
    MEDECIN = "medecin"
    ADMINISTRATEUR = "administrateur"

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(RoleEnum), nullable=False, default=RoleEnum.MEDECIN)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    last_login = db.Column(db.DateTime)
    date_modification = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    # Informations professionnelles
    nom = db.Column(db.String(100))
    prenom = db.Column(db.String(100))
    specialite = db.Column(db.String(100))
    numero_ordre = db.Column(db.String(50))
    etablissement = db.Column(db.String(200))

    # Sécurité avancée
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(32))
    backup_codes = db.Column(db.Text)
    last_2fa_use = db.Column(db.DateTime)
    failed_login_attempts = db.Column(db.Integer, default=0)
    account_locked_until = db.Column(db.DateTime)
    password_reset_token = db.Column(db.String(100))
    password_reset_expires = db.Column(db.DateTime)
    email_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(100))

    # Pour les patients : lien vers leur fiche patient
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=True)
    patient_profile = db.relationship('Patient', backref=db.backref('user_account', uselist=False), uselist=False)

    # Pour les médecins : leurs analyses (liées via AnalyseResult.user_id)
    analyses = db.relationship(
        'AnalyseResult',
        foreign_keys='AnalyseResult.user_id',
        backref=db.backref('medecin', lazy=True),
        lazy=True
    )

    def __repr__(self):
        return f"User('{self.username}', role='{self.role.value}')"
    
    @property
    def full_name(self):
        parts = [self.prenom, self.nom]
        return " ".join([p for p in parts if p]) or self.username

    @property
    def date_creation(self):
        return self.created_at

    @date_creation.setter
    def date_creation(self, value):
        self.created_at = value

    @property
    def derniere_connexion(self):
        return self.last_login

    @derniere_connexion.setter
    def derniere_connexion(self, value):
        self.last_login = value

    def is_medecin(self):
        return self.role == RoleEnum.MEDECIN
    
    def is_patient(self):
        return self.role == RoleEnum.PATIENT
    
    def is_admin(self):
        return self.role == RoleEnum.ADMINISTRATEUR
    
    @property
    def unread_notifications_count(self):
        """Retourne le nombre de notifications non lues"""
        return len([n for n in self.notifications if not n.lu])

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100))
    date_naissance = db.Column(db.Date)
    sexe = db.Column(db.String(1)) # M/F
    telephone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    adresse = db.Column(db.Text)
    numero_securite_sociale = db.Column(db.String(20))
    groupe_sanguin = db.Column(db.String(3))
    
    # Informations médicales
    antecedents_medicaux = db.Column(db.Text)
    allergies = db.Column(db.Text)
    medecin_traitant = db.Column(db.String(200))
    data_encrypted = db.Column(db.Boolean, default=False)
    consent_given = db.Column(db.Boolean, default=False)
    consent_date = db.Column(db.DateTime)
    data_retention_until = db.Column(db.DateTime)
    anonymized = db.Column(db.Boolean, default=False)
    anonymized_date = db.Column(db.DateTime)
    
    # Métadonnées
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    
    # Relations
    analyses = db.relationship('AnalyseResult', backref='patient', lazy=True)

    def __repr__(self):
        return f"Patient('{self.nom} {self.prenom}')"
    
    @property
    def date_creation(self):
        return self.created_at

    @date_creation.setter
    def date_creation(self, value):
        self.created_at = value

    @property
    def date_modification(self):
        return self.updated_at

    @date_modification.setter
    def date_modification(self, value):
        self.updated_at = value

    @property
    def age(self):
        """Calcule l'âge du patient en années"""
        if self.date_naissance:
            from datetime import date
            today = date.today()
            return today.year - self.date_naissance.year - ((today.month, today.day) < (self.date_naissance.month, self.date_naissance.day))
        return None

class AnalyseResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_path = db.Column(db.String(255), nullable=False)
    date_analyse = db.Column(db.DateTime, nullable=False, default=utcnow)
    test_positif = db.Column(db.Boolean, nullable=False)
    type_anomalie = db.Column(db.String(200), nullable=True)
    recommandation = db.Column(db.Text, nullable=True)
    resultat_global = db.Column(db.Text, nullable=True)
    confiance_score = db.Column(db.Float, nullable=True)
    image_originale = db.Column(db.String(255), nullable=True)
    image_resultat = db.Column(db.String(255), nullable=True)
    resultats_json = db.Column(db.JSON, nullable=True)
    cell_stats = db.Column(db.JSON, nullable=True)
    legend = db.Column(db.JSON, nullable=True)
    
    # Commentaire médical ajouté par le médecin
    commentaire_medecin = db.Column(db.Text, nullable=True)
    
    # Statut de validation
    statut = db.Column(db.String(20), default='EN_ATTENTE') # EN_ATTENTE, VALIDE, REJETE
    data_encrypted = db.Column(db.Boolean, default=False)
    checksum = db.Column(db.String(64))
    signed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    signature_date = db.Column(db.DateTime)
    access_restricted = db.Column(db.Boolean, default=False)
    
    # Relations
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    signataire = db.relationship('User', foreign_keys=[signed_by])
    
    # Métadonnées
    image_filename = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    def __repr__(self):
        return f"AnalyseResult(date_analyse='{self.date_analyse}', test_positif={self.test_positif})"

    @property
    def anomalies_detectees(self):
        return bool(self.test_positif or (self.type_anomalie and self.type_anomalie.strip()))

    @property
    def date_creation(self):
        return self.created_at

    @date_creation.setter
    def date_creation(self, value):
        self.created_at = value

    @property
    def date_modification(self):
        return self.updated_at

    @date_modification.setter
    def date_modification(self, value):
        self.updated_at = value

class AuditLog(db.Model):
    """Table pour l'audit trail - historique des actions"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False) # CREATE, READ, UPDATE, DELETE
    resource_type = db.Column(db.String(50), nullable=False) # Patient, AnalyseResult, etc.
    resource_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.JSON, nullable=True) # Détails de l'action en JSON
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=utcnow)
    
    user = db.relationship('User', backref='audit_logs')

class Notification(db.Model):
    """Table pour les notifications aux utilisateurs"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    titre = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type_notification = db.Column(db.String(50), nullable=False) # ANALYSE_DISPONIBLE, ANOMALIE_GRAVE, etc.
    lu = db.Column(db.Boolean, default=False)
    analyse_id = db.Column(db.Integer, db.ForeignKey('analyse_result.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    
    user = db.relationship('User', backref='notifications')
    analyse = db.relationship('AnalyseResult', backref='notifications')

class Annotation(db.Model):
    """Table pour les annotations/corrections des chercheurs"""
    id = db.Column(db.Integer, primary_key=True)
    analyse_id = db.Column(db.Integer, db.ForeignKey('analyse_result.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False, default='MANUAL') # e.g., 'RESEARCH', 'VALIDATION', 'MANUAL'
    correction_proposee = db.Column(db.String(200), nullable=True) # Correction du diagnostic
    commentaire = db.Column(db.Text, nullable=True)
    confiance = db.Column(db.Float, nullable=True) # Niveau de confiance de 0 à 1
    statut = db.Column(db.String(20), default='EN_COURS') # EN_COURS, APPROUVE, REJETE
    created_at = db.Column(db.DateTime, default=utcnow)
    
    analyse = db.relationship('AnalyseResult', backref='annotations')
    annotateur = db.relationship('User', backref='annotations')
