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
os.makedirs('instance', exist_ok=True)  # Dossier pour la base de données SQLite


db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'routes.login'
login_manager.login_message_category = 'info'
login_manager.init_app(app)

app.register_blueprint(routes)

from models import User, Patient, AnalyseResult # noqa

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.cli.command('init-db')
def init_db_command():
    """Créer les tables de la base de données."""
    db.create_all()
    print('Base de données initialisée.')

def create_database():
    with app.app_context():
        try:
            # Vérifier si les tables existent déjà
            db.create_all()
            print('Base de données initialisée avec succès!')
        except Exception as e:
            print(f'Erreur lors de la création de la base de données: {e}')

# Créer la base de données au démarrage de l'application
create_database()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)