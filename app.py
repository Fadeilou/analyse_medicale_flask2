from flask import Flask
from routes import routes
from models import db # Importe l'instance de base de données depuis models.py
from flask_login import LoginManager
from config import get_config
import os
import logging
from logging.handlers import RotatingFileHandler


def create_app():
    """Factory pour créer l'application Flask"""
    app = Flask(__name__)
    
    # Charger la configuration
    config_class = get_config()
    app.config.from_object(config_class)
    
    # Configuration des dossiers
    app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploaded_images')
    app.config['RESULTS_FOLDER'] = os.path.join(app.static_folder, 'results_images')
    
    # Créer les dossiers nécessaires
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)
    os.makedirs('instance', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    return app

app = create_app()


# Initialiser les extensions
db.init_app(app)

# Configuration Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'routes.login'
login_manager.login_message = 'Vous devez vous connecter pour accéder à cette page.'
login_manager.login_message_category = 'info'
login_manager.init_app(app)

# Enregistrer les blueprints
app.register_blueprint(routes)

# Initialiser le monitoring
from monitoring import init_monitoring
init_monitoring(app)

# Imports pour éviter les erreurs de référence circulaire
from models import User, Patient, AnalyseResult, Notification, AuditLog, Annotation

@login_manager.user_loader
def load_user(user_id):
    """Charge un utilisateur par son ID pour Flask-Login"""
    try:
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None

# Configuration des logs
def setup_logging(app):
    """Configure le système de logs"""
    if not app.debug and not app.testing:
        # Logs rotatifs pour éviter les gros fichiers
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler(
            'logs/app.log', 
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Application médicale démarrée')

setup_logging(app)

@app.cli.command('init-db')
def init_db_command():
    """Commande CLI pour initialiser la base de données"""
    with app.app_context():
        try:
            db.create_all()
            print('✅ Base de données initialisée avec succès!')
        except Exception as e:
            print(f'❌ Erreur lors de l\'initialisation: {e}')

@app.cli.command('create-admin')
def create_admin_command():
    """Commande CLI pour créer un administrateur"""
    from werkzeug.security import generate_password_hash
    from models import RoleEnum
    
    with app.app_context():
        try:
            # Vérifier si un admin existe déjà
            admin_exists = User.query.filter_by(role=RoleEnum.ADMINISTRATEUR).first()
            if admin_exists:
                print('ℹ️  Un administrateur existe déjà.')
                return
            
            admin = User(
                username='admin',
                email='admin@medicale.com',
                password=generate_password_hash('admin123'),
                role=RoleEnum.ADMINISTRATEUR,
                is_active=True
            )
            db.session.add(admin)
            db.session.commit()
            print('✅ Administrateur créé: admin / admin123')
        except Exception as e:
            print(f'❌ Erreur: {e}')
            db.session.rollback()

def create_database():
    """Initialise la base de données au démarrage"""
    with app.app_context():
        try:
            db.create_all()
            app.logger.info('Base de données initialisée avec succès')
            
            # Vérifier et créer les données par défaut
            create_default_data()
            
        except Exception as e:
            app.logger.error(f'Erreur lors de la création de la base de données: {e}')

def create_default_data():
    """Crée les données par défaut si elles n'existent pas"""
    from models import User, Patient, RoleEnum, Notification
    from werkzeug.security import generate_password_hash
    from datetime import datetime, date, timezone
    
    try:
        # Vérifier si des utilisateurs existent déjà
        if User.query.first():
            app.logger.info('Des utilisateurs existent déjà, pas d\'initialisation des données de test.')
            return
        
        app.logger.info('Création des utilisateurs de base...')
        
        # Créer un administrateur par défaut
        admin = User(
            username='admin',
            email='admin@medicale.com',
            password=generate_password_hash('admin123'),
            role=RoleEnum.ADMINISTRATEUR,
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(admin)
        
        # Créer un médecin par défaut
        medecin = User(
            username='dr_martin',
            email='medecin@medicale.com',
            password=generate_password_hash('medecin123'),
            role=RoleEnum.MEDECIN,
            is_active=True,
            created_at=datetime.now(timezone.utc)
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
            created_at=datetime.now(timezone.utc)
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
            created_at=datetime.now(timezone.utc)
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
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(user_patient)
        
        # Commitons les utilisateurs et patients d'abord
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
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(notification)
        
        db.session.commit()
        
        app.logger.info('Données par défaut créées avec succès!')
        app.logger.info('Comptes créés: admin/admin123, dr_martin/medecin123, jean_dupont/patient123')
        
    except Exception as e:
        app.logger.error(f'Erreur lors de la création des données par défaut: {e}')
        db.session.rollback()

# Créer la base de données au démarrage
create_database()

# Gestionnaires d'erreurs
@app.errorhandler(404)
def not_found_error(error):
    from flask import render_template
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    from flask import render_template
    db.session.rollback()
    app.logger.error(f'Erreur serveur: {error}')
    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def forbidden_error(error):
    from flask import render_template
    return render_template('errors/403.html'), 403
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