from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, HiddenField
from wtforms.validators import DataRequired, Length, Optional
from wtforms.widgets import TextArea

class AnnotationForm(FlaskForm):
    """Formulaire pour annoter une analyse médicale"""
    
    annotation_type = SelectField(
        'Type d\'annotation',
        choices=[
            ('research', 'Recherche'),
            ('quality', 'Contrôle qualité'),
            ('training', 'Formation'),
            ('validation', 'Validation')
        ],
        default='research',
        validators=[DataRequired()]
    )
    
    ia_evaluation = SelectField(
        'Évaluation de l\'IA',
        choices=[
            ('correct', 'Correct - L\'IA a bien identifié'),
            ('partially_correct', 'Partiellement correct - Détection incomplète'),
            ('incorrect', 'Incorrect - Erreur de détection'),
            ('false_positive', 'Faux positif - Anomalie incorrectement détectée'),
            ('false_negative', 'Faux négatif - Anomalie manquée'),
            ('unclear', 'Non déterminable - Image de qualité insuffisante')
        ],
        validators=[DataRequired()]
    )
    
    annotation = TextAreaField(
        'Annotation détaillée',
        validators=[DataRequired(), Length(min=10, max=2000)],
        description='Décrivez vos observations, corrections ou commentaires sur cette analyse'
    )
    
    tags = StringField(
        'Tags',
        validators=[Optional(), Length(max=500)],
        description='Mots-clés séparés par des virgules'
    )
    
    statut = SelectField(
        'Statut de l\'annotation',
        choices=[
            ('draft', 'Brouillon'),
            ('pending', 'En cours de révision'),
            ('validated', 'Validée'),
            ('rejected', 'Rejetée')
        ],
        default='pending',
        validators=[DataRequired()]
    )
    
    notes_privees = TextAreaField(
        'Notes privées',
        validators=[Optional(), Length(max=1000)],
        description='Notes internes non visibles dans les exports'
    )
    
    analyse_id = HiddenField()

class PatientForm(FlaskForm):
    """Formulaire pour créer/modifier un patient"""
    
    nom = StringField(
        'Nom',
        validators=[DataRequired(), Length(min=2, max=100)]
    )
    
    prenom = StringField(
        'Prénom', 
        validators=[DataRequired(), Length(min=2, max=100)]
    )
    
    date_naissance = StringField(
        'Date de naissance',
        validators=[Optional()],
        description='Format: JJ/MM/AAAA'
    )
    
    sexe = SelectField(
        'Sexe',
        choices=[
            ('', 'Non spécifié'),
            ('M', 'Masculin'),
            ('F', 'Féminin')
        ],
        validators=[Optional()]
    )
    
    numero_securite_sociale = StringField(
        'Numéro de Sécurité Sociale',
        validators=[Optional(), Length(min=13, max=15)],
        description='13 chiffres'
    )
    
    email = StringField(
        'Email',
        validators=[Optional(), Length(max=120)]
    )
    
    telephone = StringField(
        'Téléphone',
        validators=[Optional(), Length(max=20)]
    )
    
    adresse = TextAreaField(
        'Adresse',
        validators=[Optional(), Length(max=500)]
    )
    
    medecin_traitant = StringField(
        'Médecin traitant',
        validators=[Optional(), Length(max=100)]
    )
    
    groupe_sanguin = SelectField(
        'Groupe sanguin',
        choices=[
            ('', 'Non spécifié'),
            ('A+', 'A+'),
            ('A-', 'A-'),
            ('B+', 'B+'),
            ('B-', 'B-'),
            ('AB+', 'AB+'),
            ('AB-', 'AB-'),
            ('O+', 'O+'),
            ('O-', 'O-')
        ],
        validators=[Optional()]
    )
    
    allergies = TextAreaField(
        'Allergies',
        validators=[Optional(), Length(max=1000)]
    )
    
    antecedents_medicaux = TextAreaField(
        'Antécédents médicaux',
        validators=[Optional(), Length(max=2000)]
    )

class CommentForm(FlaskForm):
    """Formulaire pour ajouter un commentaire médical"""
    
    commentaire = TextAreaField(
        'Commentaire médical',
        validators=[DataRequired(), Length(min=10, max=2000)],
        widget=TextArea()
    )
    
    visible_patient = SelectField(
        'Visible pour le patient',
        choices=[
            ('oui', 'Oui - Le patient peut voir ce commentaire'),
            ('non', 'Non - Commentaire interne uniquement')
        ],
        default='non',
        validators=[DataRequired()]
    )
    
    type_commentaire = SelectField(
        'Type de commentaire',
        choices=[
            ('observation', 'Observation clinique'),
            ('diagnostic', 'Diagnostic'),
            ('recommandation', 'Recommandation'),
            ('suivi', 'Suivi'),
            ('note', 'Note générale')
        ],
        default='observation',
        validators=[DataRequired()]
    )

class UserForm(FlaskForm):
    """Formulaire pour créer/modifier un utilisateur (admin)"""
    
    nom = StringField(
        'Nom',
        validators=[DataRequired(), Length(min=2, max=100)]
    )
    
    prenom = StringField(
        'Prénom',
        validators=[DataRequired(), Length(min=2, max=100)]
    )
    
    email = StringField(
        'Email',
        validators=[DataRequired(), Length(max=120)]
    )
    
    role = SelectField(
        'Rôle',
        choices=[
            ('medecin', 'Médecin'),
            ('patient', 'Patient'),
            ('administrateur', 'Administrateur')
        ],
        validators=[DataRequired()]
    )
    
    specialite = StringField(
        'Spécialité',
        validators=[Optional(), Length(max=100)],
        description='Pour les médecins uniquement'
    )
    
    numero_ordre = StringField(
        'Numéro d\'ordre',
        validators=[Optional(), Length(max=50)],
        description='Numéro d\'ordre professionnel pour les médecins'
    )
    
    is_active = SelectField(
        'Statut du compte',
        choices=[
            ('True', 'Actif'),
            ('False', 'Inactif')
        ],
        default='True',
        validators=[DataRequired()]
    )
    
    etablissement = StringField(
        'Établissement',
        validators=[Optional(), Length(max=200)]
    )
    
    send_welcome_email = SelectField(
        'Envoyer email de bienvenue',
        choices=[
            ('True', 'Oui'),
            ('False', 'Non')
        ],
        default='True'
    )

class BulkAnnotationForm(FlaskForm):
    """Formulaire pour l'annotation en lot"""
    
    annotation_type = SelectField(
        'Type d\'annotation',
        choices=[
            ('research', 'Recherche'),
            ('quality', 'Contrôle qualité'),
            ('training', 'Formation'),
            ('validation', 'Validation')
        ],
        default='research',
        validators=[DataRequired()]
    )
    
    annotation_template = TextAreaField(
        'Modèle d\'annotation',
        validators=[DataRequired(), Length(min=10, max=1000)],
        description='Cette annotation sera appliquée à toutes les analyses sélectionnées'
    )
    
    tags = StringField(
        'Tags communs',
        validators=[Optional(), Length(max=500)],
        description='Tags qui seront appliqués à toutes les analyses'
    )
    
    statut = SelectField(
        'Statut',
        choices=[
            ('pending', 'En cours de révision'),
            ('validated', 'Validée')
        ],
        default='pending',
        validators=[DataRequired()]
    )
    
    analysis_ids = HiddenField(
        'IDs des analyses',
        validators=[DataRequired()]
    )
