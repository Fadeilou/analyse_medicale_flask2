"""
Configuration centralisée pour l'application Flask
Gère les variables d'environnement et les paramètres de sécurité
"""
import os
from datetime import timedelta

class Config:
    """Configuration de base"""
    
    # Clé secrète - IMPORTANT: Changer en production !
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'une_cle_secrete_tres_secrete_a_changer'
    
    # Configuration de la base de données
    # En production, utiliser la variable d'environnement DATABASE_URL
    # DATABASE_URL = os.environ.get('DATABASE_URL') or \
    #     'postgresql://postgres.ckxdpngmuuqdzdlsdiqb:iXBWWRCxGyWczCQLZkrbgkiTDqcmpVpecO@aws-0-eu-north-1.pooler.supabase.com:6543/postgres?sslmode=require'
    
    DATABASE_URL = os.environ.get('DATABASE_URL') or \
        'postgresql://blood_wki0_user:mER5oOdlXs5M1LlFq5zgryN1hrBMyPgQ@dpg-d48rolur433s73a8eh00-a.oregon-postgres.render.com/blood_wki0'
    

    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 20,
        'max_overflow': 0
    }
    
    # Configuration des uploads
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = 'static/uploaded_images'
    RESULTS_FOLDER = 'static/results_images'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Configuration IA
    AI_MODEL_PATH = os.environ.get('AI_MODEL_PATH') or 'best.pt'
    AI_CONFIDENCE_THRESHOLD = float(os.environ.get('AI_CONFIDENCE_THRESHOLD', '0.4'))
    
    # Configuration email (pour les notifications)
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@medicale.com'
    
    # Configuration SMS (pour les notifications)
    SMS_API_KEY = os.environ.get('SMS_API_KEY')
    SMS_API_SECRET = os.environ.get('SMS_API_SECRET')
    
    # Configuration de sécurité
    SESSION_PERMANENT = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Configuration Flask-Login
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    REMEMBER_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    REMEMBER_COOKIE_HTTPONLY = True
    
    # Configuration des logs
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.log')
    
    # Configuration de l'environnement
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1', 'on']
    TESTING = False
    
    # Configuration pour Render.com ou autres plateformes cloud
    PORT = int(os.environ.get('PORT', 5000))
    HOST = os.environ.get('HOST', '0.0.0.0')

class DevelopmentConfig(Config):
    """Configuration pour le développement"""
    DEBUG = True
    SQLALCHEMY_ECHO = False  # Set to True pour voir les requêtes SQL

class ProductionConfig(Config):
    """Configuration pour la production"""
    DEBUG = False
    TESTING = False
    
    # Sécurité renforcée en production
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    
    # Logs plus détaillés en production
    LOG_LEVEL = 'WARNING'

class TestingConfig(Config):
    """Configuration pour les tests"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Dictionnaire pour faciliter la sélection de config
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Retourne la configuration appropriée selon l'environnement"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])
