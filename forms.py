from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, Regexp
from models import User # Importe le modèle User pour la validation d'username

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