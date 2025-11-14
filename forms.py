from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, DateField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, Regexp, Email, Optional
from models import User, RoleEnum # Importe le modèle User pour la validation d'username

class RegistrationForm(FlaskForm):
    username = StringField('Nom d\'utilisateur',
                           validators=[
                               DataRequired(message='Le nom d\'utilisateur est requis.'), 
                               Length(min=3, max=20, message='Le nom d\'utilisateur doit contenir entre 3 et 20 caractères.'),
                               Regexp('^[A-Za-z0-9_]+$', message='Le nom d\'utilisateur ne peut contenir que des lettres, chiffres et underscores.')
                           ])

    password = PasswordField('Mot de passe', 
                           validators=[
                               DataRequired(message='Le mot de passe est requis.'),
                               Length(min=6, message='Le mot de passe doit contenir au moins 6 caractères.')
                           ])
    confirm_password = PasswordField('Confirmer le mot de passe',
                                     validators=[
                                         DataRequired(message='La confirmation du mot de passe est requise.'), 
                                         EqualTo('password', message='Les mots de passe doivent correspondre.')
                                     ])

    submit = SubmitField('S\'inscrire')

    def validate_username(self, username): # Validation personnalisée pour vérifier si le nom d'utilisateur existe déjà
        user = User.query.filter_by(username=username.data).first() # Recherche un utilisateur avec ce nom d'utilisateur dans la base de données
        if user:
            raise ValidationError('Ce nom d\'utilisateur est déjà pris. Veuillez en choisir un autre.') # Lève une erreur si l'utilisateur existe déjà


class AdminUserForm(FlaskForm):
    """Formulaire utilisé par un administrateur pour créer un compte utilisateur"""

    nom = StringField('Nom', validators=[DataRequired(), Length(min=2, max=100)])
    prenom = StringField('Prénom', validators=[DataRequired(), Length(min=2, max=100)])
    username = StringField('Nom d\'utilisateur', validators=[DataRequired(), Length(min=3, max=50), Regexp('^[A-Za-z0-9_]+$', message='Seuls lettres, chiffres et underscore sont autorisés.')])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    role = SelectField('Rôle', choices=[(RoleEnum.MEDECIN.value, 'Médecin'), (RoleEnum.PATIENT.value, 'Patient'), (RoleEnum.ADMINISTRATEUR.value, 'Administrateur')], validators=[DataRequired()])
    password = PasswordField('Mot de passe', validators=[DataRequired(), Length(min=6)])
    password_confirm = PasswordField('Confirmer le mot de passe', validators=[DataRequired(), EqualTo('password', message='Les mots de passe doivent correspondre.')])
    date_naissance = DateField('Date de naissance', format='%Y-%m-%d', validators=[Optional()])
    telephone = StringField('Téléphone', validators=[Optional(), Length(max=20)])
    adresse = TextAreaField('Adresse', validators=[Optional(), Length(max=500)])

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Ce nom d\'utilisateur est déjà utilisé.')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Cet email est déjà utilisé.')
