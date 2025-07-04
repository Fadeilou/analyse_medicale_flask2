from flask import Flask
from routes import routes
from models import db # Importe l'instance de base de données depuis models.py
from flask_login import LoginManager
import os


app = Flask(__name__)
app.config['SECRET_KEY'] = 'une_cle_secrete_tres_secrete'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# app.config['UPLOAD_FOLDER'] = 'static/uploaded_images' # Configure UPLOAD_FOLDER here

app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploaded_images') # Chemin plus robuste
app.config['RESULTS_FOLDER'] = os.path.join(app.static_folder, 'results_images') # Chemin vers les images résultat

# Créer les dossiers si n'existent pas au démarrage
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)


db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'routes.login'
login_manager.login_message_category = 'info'
login_manager.init_app(app)

app.register_blueprint(routes)

from models import User, Patient, AnalyseResult # noqa

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def create_database():
    with app.app_context():
        db.create_all()
        print('Base de données créée!')

if __name__ == '__main__':
    create_database()
    app.run(debug=True)