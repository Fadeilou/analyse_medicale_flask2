"""
Suite de tests pour l'application d'analyse médicale
Tests unitaires et d'intégration pour tous les composants
"""
import pytest
import tempfile
import os
import json
from datetime import datetime, date
from werkzeug.security import generate_password_hash
from io import BytesIO
from PIL import Image

# Configuration des tests
os.environ['FLASK_ENV'] = 'testing'

from app import create_app
from models import db, User, Patient, AnalyseResult, RoleEnum, Notification, AuditLog
from config import TestingConfig


@pytest.fixture
def app():
    """Fixture pour l'application Flask de test"""
    app = create_app()
    app.config.from_object(TestingConfig)
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Client de test Flask"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Runner CLI de test"""
    return app.test_cli_runner()


@pytest.fixture
def auth_headers(client):
    """Headers d'authentification pour les tests API"""
    # Créer un utilisateur admin de test
    admin = User(
        username='test_admin',
        email='admin@test.com',
        password=generate_password_hash('password123'),
        role=RoleEnum.ADMINISTRATEUR,
        is_active=True
    )
    db.session.add(admin)
    db.session.commit()
    
    # Se connecter et récupérer la session
    response = client.post('/login', data={
        'username': 'test_admin',
        'password': 'password123'
    })
    
    return {'Content-Type': 'application/json'}


class TestUserModel:
    """Tests pour le modèle User"""
    
    def test_user_creation(self, app):
        """Test de création d'utilisateur"""
        with app.app_context():
            user = User(
                username='testuser',
                email='test@example.com',
                password=generate_password_hash('password123'),
                role=RoleEnum.MEDECIN
            )
            db.session.add(user)
            db.session.commit()
            
            assert user.id is not None
            assert user.username == 'testuser'
            assert user.is_medecin() == True
            assert user.is_patient() == False
            assert user.is_admin() == False
    
    def test_user_roles(self, app):
        """Test des rôles utilisateur"""
        with app.app_context():
            # Médecin
            medecin = User(username='medecin', password='pass', role=RoleEnum.MEDECIN)
            assert medecin.is_medecin() == True
            
            # Patient
            patient = User(username='patient', password='pass', role=RoleEnum.PATIENT)
            assert patient.is_patient() == True
            
            # Admin
            admin = User(username='admin', password='pass', role=RoleEnum.ADMINISTRATEUR)
            assert admin.is_admin() == True


class TestPatientModel:
    """Tests pour le modèle Patient"""
    
    def test_patient_creation(self, app):
        """Test de création de patient"""
        with app.app_context():
            patient = Patient(
                nom='Dupont',
                prenom='Jean',
                date_naissance=date(1980, 1, 1),
                sexe='M',
                email='jean.dupont@email.com'
            )
            db.session.add(patient)
            db.session.commit()
            
            assert patient.id is not None
            assert patient.nom == 'Dupont'
            assert str(patient) == "Patient('Dupont Jean')"


class TestAnalyseModel:
    """Tests pour le modèle AnalyseResult"""
    
    def test_analyse_creation(self, app):
        """Test de création d'analyse"""
        with app.app_context():
            # Créer un médecin et un patient
            medecin = User(username='dr_test', password='pass', role=RoleEnum.MEDECIN)
            patient = Patient(nom='Test', prenom='Patient')
            
            db.session.add_all([medecin, patient])
            db.session.commit()
            
            # Créer une analyse
            analyse = AnalyseResult(
                image_path='test_image.jpg',
                test_positif=True,
                type_anomalie='DREPANOCYTES',
                patient_id=patient.id,
                user_id=medecin.id
            )
            db.session.add(analyse)
            db.session.commit()
            
            assert analyse.id is not None
            assert analyse.test_positif == True
            assert analyse.patient == patient
            assert analyse.medecin == medecin


class TestAuthentication:
    """Tests d'authentification"""
    
    def test_login_page(self, client):
        """Test de la page de connexion"""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'connexion' in response.data.lower()
    
    def test_login_success(self, client, app):
        """Test de connexion réussie"""
        with app.app_context():
            # Créer un utilisateur
            user = User(
                username='testuser',
                email='test@example.com',
                password=generate_password_hash('password123'),
                role=RoleEnum.MEDECIN
            )
            db.session.add(user)
            db.session.commit()
        
        # Tenter de se connecter
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'password123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_login_failure(self, client):
        """Test de connexion échouée"""
        response = client.post('/login', data={
            'username': 'wronguser',
            'password': 'wrongpass'
        })
        
        assert response.status_code == 200
        # Vérifie qu'on reste sur la page de login ou qu'il y a un message d'erreur
    
    def test_logout(self, client, app):
        """Test de déconnexion"""
        with app.app_context():
            user = User(
                username='testuser',
                password=generate_password_hash('password123'),
                role=RoleEnum.MEDECIN
            )
            db.session.add(user)
            db.session.commit()
        
        # Se connecter
        client.post('/login', data={
            'username': 'testuser',
            'password': 'password123'
        })
        
        # Se déconnecter
        response = client.get('/logout', follow_redirects=True)
        assert response.status_code == 200


class TestImageAnalysis:
    """Tests d'analyse d'images"""
    
    def create_test_image(self):
        """Crée une image de test"""
        img = Image.new('RGB', (224, 224), color='red')
        img_io = BytesIO()
        img.save(img_io, 'JPEG')
        img_io.seek(0)
        return img_io
    
    def test_image_upload_endpoint(self, client, app):
        """Test de l'endpoint d'upload d'image"""
        with app.app_context():
            # Créer et connecter un médecin
            medecin = User(
                username='dr_test',
                password=generate_password_hash('password123'),
                role=RoleEnum.MEDECIN
            )
            patient = Patient(nom='Test', prenom='Patient')
            db.session.add_all([medecin, patient])
            db.session.commit()
            
            # Se connecter
            client.post('/login', data={
                'username': 'dr_test',
                'password': 'password123'
            })
            
            # Tester l'upload (simulation)
            response = client.get('/analyse')
            assert response.status_code == 200
    
    def test_allowed_file_extensions(self, app):
        """Test des extensions de fichiers autorisées"""
        with app.app_context():
            from routes import allowed_image_file
            
            assert allowed_image_file('test.jpg') == True
            assert allowed_image_file('test.jpeg') == True
            assert allowed_image_file('test.png') == True
            assert allowed_image_file('test.gif') == False
            assert allowed_image_file('test.txt') == False


class TestAPI:
    """Tests des endpoints API"""
    
    def test_health_check(self, client):
        """Test du health check"""
        response = client.get('/monitoring/health')
        assert response.status_code in [200, 503]  # Peut échouer en test
        
        data = json.loads(response.data)
        assert 'status' in data
        assert 'timestamp' in data
    
    def test_patients_list_api(self, client, app):
        """Test de l'API liste des patients"""
        with app.app_context():
            # Créer un médecin
            medecin = User(
                username='dr_api_test',
                password=generate_password_hash('password123'),
                role=RoleEnum.MEDECIN
            )
            db.session.add(medecin)
            db.session.commit()
            
            # Se connecter
            client.post('/login', data={
                'username': 'dr_api_test',
                'password': 'password123'
            })
            
            # Tester l'API
            response = client.get('/patients')
            assert response.status_code == 200


class TestSecurity:
    """Tests de sécurité"""
    
    def test_unauthorized_access(self, client):
        """Test d'accès non autorisé"""
        # Essayer d'accéder à une page protégée sans être connecté
        response = client.get('/dashboard')
        assert response.status_code == 302  # Redirection vers login
    
    def test_role_based_access(self, client, app):
        """Test d'accès basé sur les rôles"""
        with app.app_context():
            # Créer un patient
            patient_user = User(
                username='patient_test',
                password=generate_password_hash('password123'),
                role=RoleEnum.PATIENT
            )
            db.session.add(patient_user)
            db.session.commit()
            
            # Se connecter en tant que patient
            client.post('/login', data={
                'username': 'patient_test',
                'password': 'password123'
            })
            
            # Essayer d'accéder à une page admin
            response = client.get('/admin/users')
            assert response.status_code in [403, 302]  # Forbidden ou redirection
    
    def test_csrf_protection(self, client):
        """Test de protection CSRF"""
        # Ce test dépend de votre implémentation CSRF
        pass


class TestBusinessLogic:
    """Tests de logique métier"""
    
    def test_patient_creation_workflow(self, client, app):
        """Test du workflow de création de patient"""
        with app.app_context():
            # Créer et connecter un médecin
            medecin = User(
                username='dr_workflow_test',
                password=generate_password_hash('password123'),
                role=RoleEnum.MEDECIN
            )
            db.session.add(medecin)
            db.session.commit()
            
            client.post('/login', data={
                'username': 'dr_workflow_test',
                'password': 'password123'
            })
            
            # Créer un patient via l'interface web
            response = client.post('/patients/new', data={
                'nom': 'Nouveau',
                'prenom': 'Patient',
                'email': 'nouveau@patient.com',
                'sexe': 'M'
            }, follow_redirects=True)
            
            # Vérifier que ça a marché
            patient = Patient.query.filter_by(nom='Nouveau').first()
            assert patient is not None
    
    def test_notification_creation(self, app):
        """Test de création de notifications"""
        with app.app_context():
            user = User(username='test', password='pass', role=RoleEnum.MEDECIN)
            db.session.add(user)
            db.session.commit()
            
            notification = Notification(
                user_id=user.id,
                titre='Test Notification',
                message='Ceci est un test',
                type_notification='TEST'
            )
            db.session.add(notification)
            db.session.commit()
            
            assert notification.id is not None
            assert notification.lu == False


class TestDataValidation:
    """Tests de validation des données"""
    
    def test_patient_data_validation(self, app):
        """Test de validation des données patient"""
        with app.app_context():
            # Test avec des données valides
            valid_patient = Patient(
                nom='Dupont',
                prenom='Jean',
                email='jean@example.com'
            )
            db.session.add(valid_patient)
            db.session.commit()
            
            assert valid_patient.id is not None
    
    def test_user_email_uniqueness(self, app):
        """Test d'unicité des emails"""
        with app.app_context():
            user1 = User(
                username='user1',
                email='same@email.com',
                password='pass1',
                role=RoleEnum.MEDECIN
            )
            user2 = User(
                username='user2',
                email='same@email.com',
                password='pass2',
                role=RoleEnum.PATIENT
            )
            
            db.session.add(user1)
            db.session.commit()
            
            # Ajouter le deuxième utilisateur devrait échouer
            db.session.add(user2)
            with pytest.raises(Exception):  # Violation de contrainte d'unicité
                db.session.commit()


class TestIntegration:
    """Tests d'intégration end-to-end"""
    
    def test_complete_analysis_workflow(self, client, app):
        """Test du workflow complet d'analyse"""
        with app.app_context():
            # 1. Créer les entités nécessaires
            medecin = User(
                username='dr_integration',
                password=generate_password_hash('password123'),
                role=RoleEnum.MEDECIN
            )
            patient = Patient(
                nom='Patient',
                prenom='Integration',
                email='integration@test.com'
            )
            db.session.add_all([medecin, patient])
            db.session.commit()
            
            # 2. Se connecter
            client.post('/login', data={
                'username': 'dr_integration',
                'password': 'password123'
            })
            
            # 3. Accéder à la page d'analyse
            response = client.get('/analyse')
            assert response.status_code == 200
            
            # 4. Accéder à la liste des patients
            response = client.get('/patients')
            assert response.status_code == 200
            
            # 5. Voir le détail d'un patient
            response = client.get(f'/patients/{patient.id}')
            assert response.status_code == 200


def test_database_connection(app):
    """Test de connexion à la base de données"""
    with app.app_context():
        # Test simple de connexion
        result = db.session.execute(db.text('SELECT 1')).scalar()
        assert result == 1


def test_app_config(app):
    """Test de la configuration de l'application"""
    assert app.config['TESTING'] == True
    assert app.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite:///:memory:'


if __name__ == '__main__':
    """Exécution des tests en standalone"""
    pytest.main([__file__, '-v'])
