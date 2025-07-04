from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, ValidationError
from models import User

class LoginForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', 
                           validators=[DataRequired(message='Le nom d\'utilisateur est requis.'), 
                                     Length(min=2, max=20, message='Le nom d\'utilisateur doit contenir entre 2 et 20 caractères.')])
    password = PasswordField('Mot de passe', 
                            validators=[DataRequired(message='Le mot de passe est requis.')])
    remember_me = BooleanField('Se souvenir de moi')
    submit = SubmitField('Se Connecter')

class ForgotPasswordForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', 
                           validators=[DataRequired(message='Le nom d\'utilisateur est requis.')])
    submit = SubmitField('Réinitialiser le mot de passe')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if not user:
            raise ValidationError('Aucun compte trouvé avec ce nom d\'utilisateur.')

class ResetPasswordForm(FlaskForm):
    new_password = PasswordField('Nouveau mot de passe', 
                               validators=[DataRequired(message='Le nouveau mot de passe est requis.'),
                                         Length(min=6, message='Le mot de passe doit contenir au moins 6 caractères.')])
    confirm_password = PasswordField('Confirmer le nouveau mot de passe',
                                   validators=[DataRequired(message='La confirmation du mot de passe est requise.')])
    submit = SubmitField('Changer le mot de passe')
    
    def validate_confirm_password(self, confirm_password):
        if self.new_password.data != confirm_password.data:
            raise ValidationError('Les mots de passe ne correspondent pas.')