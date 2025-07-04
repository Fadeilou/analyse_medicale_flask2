from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from models import User # Importe le modèle User pour la validation d'username

class RegistrationForm(FlaskForm):
    username = StringField('Nom d\'utilisateur',
                           validators=[DataRequired(), Length(min=2, max=20)]) # Validation: requis, longueur min/max

    password = PasswordField('Mot de passe', validators=[DataRequired()]) # Validation: requis
    confirm_password = PasswordField('Confirmer le mot de passe',
                                     validators=[DataRequired(), EqualTo('password', message='Les mots de passe doivent correspondre')]) # Validation: requis, doit correspondre au champ 'password'

    submit = SubmitField('S\'inscrire')

    def validate_username(self, username): # Validation personnalisée pour vérifier si le nom d'utilisateur existe déjà
        user = User.query.filter_by(username=username.data).first() # Recherche un utilisateur avec ce nom d'utilisateur dans la base de données
        if user:
            raise ValidationError('Ce nom d\'utilisateur est déjà pris. Veuillez en choisir un autre.') # Lève une erreur si l'utilisateur existe déjà