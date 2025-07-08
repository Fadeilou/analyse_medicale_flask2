#!/bin/bash

# Script de déploiement pour l'application d'analyse médicale
# Supporte les déploiements sur Render.com, Heroku, et serveurs VPS

set -e  # Arrêter en cas d'erreur

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher des messages colorés
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Vérifier les prérequis
check_prerequisites() {
    log_info "Vérification des prérequis..."
    
    # Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 n'est pas installé"
        exit 1
    fi
    
    # Pip
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 n'est pas installé"
        exit 1
    fi
    
    # Git
    if ! command -v git &> /dev/null; then
        log_warning "Git n'est pas installé (optionnel pour le développement)"
    fi
    
    log_success "Prérequis vérifiés"
}

# Installation des dépendances
install_dependencies() {
    log_info "Installation des dépendances Python..."
    
    # Créer un environnement virtuel si il n'existe pas
    if [ ! -d "venv" ]; then
        log_info "Création de l'environnement virtuel..."
        python3 -m venv venv
    fi
    
    # Activer l'environnement virtuel
    source venv/bin/activate
    
    # Mettre à jour pip
    pip install --upgrade pip
    
    # Installer les dépendances
    pip install -r requirements.txt
    
    log_success "Dépendances installées"
}

# Configuration de l'environnement
setup_environment() {
    log_info "Configuration de l'environnement..."
    
    # Créer le fichier .env si il n'existe pas
    if [ ! -f ".env" ]; then
        log_info "Création du fichier .env..."
        cat > .env << EOF
# Configuration de l'environnement
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Base de données (remplacer par vos vraies valeurs)
DATABASE_URL=postgresql://user:password@host:port/database

# Email (optionnel)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
MAIL_DEFAULT_SENDER=noreply@votre-domaine.com

# SMS (optionnel)
SMS_API_KEY=your_sms_api_key
SMS_API_SECRET=your_sms_api_secret

# IA
AI_MODEL_PATH=best.pt
AI_CONFIDENCE_THRESHOLD=0.4

# Logs
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# Sécurité
SESSION_COOKIE_SECURE=true
REMEMBER_COOKIE_SECURE=true
EOF
        log_warning "Fichier .env créé avec des valeurs par défaut. MODIFIEZ LES VALEURS !"
    fi
    
    # Créer les dossiers nécessaires
    mkdir -p logs
    mkdir -p static/uploaded_images
    mkdir -p static/results_images
    mkdir -p instance
    
    log_success "Environnement configuré"
}

# Initialisation de la base de données
init_database() {
    log_info "Initialisation de la base de données..."
    
    # Activer l'environnement virtuel
    source venv/bin/activate
    
    # Initialiser la base de données
    python3 init_db.py
    
    log_success "Base de données initialisée"
}

# Tests
run_tests() {
    log_info "Exécution des tests..."
    
    # Activer l'environnement virtuel
    source venv/bin/activate
    
    # Lancer les tests (si vous en avez)
    if [ -f "test_app.py" ]; then
        python3 -m pytest test_app.py -v
    else
        log_warning "Aucun fichier de test trouvé"
    fi
    
    # Test de santé de l'application
    log_info "Test de démarrage de l'application..."
    timeout 10s python3 -c "
from app import app
with app.app_context():
    from models import db
    try:
        db.create_all()
        print('✅ Application démarrée avec succès')
    except Exception as e:
        print(f'❌ Erreur: {e}')
        exit(1)
" || log_error "Échec du test de démarrage"
    
    log_success "Tests terminés"
}

# Déploiement pour Render.com
deploy_render() {
    log_info "Préparation pour le déploiement Render.com..."
    
    # Vérifier le fichier start.sh
    if [ ! -f "start.sh" ]; then
        log_info "Création du fichier start.sh pour Render..."
        cat > start.sh << 'EOF'
#!/bin/bash

# Script de démarrage pour Render.com
set -e

echo "🚀 Démarrage de l'application médicale..."

# Installer les dépendances si nécessaire
pip install -r requirements.txt

# Initialiser la base de données
python init_db.py

# Démarrer l'application avec Gunicorn
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 60 app:app
EOF
        chmod +x start.sh
    fi
    
    # Créer render.yaml pour le déploiement automatique
    if [ ! -f "render.yaml" ]; then
        cat > render.yaml << 'EOF'
services:
  - type: web
    name: analyse-medicale
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: ./start.sh
    envVars:
      - key: FLASK_ENV
        value: production
      - key: FLASK_DEBUG
        value: false
    healthCheckPath: /monitoring/health
EOF
    fi
    
    log_success "Configuration Render.com créée"
    log_info "Ajoutez vos variables d'environnement dans le dashboard Render"
}

# Déploiement pour Heroku
deploy_heroku() {
    log_info "Préparation pour le déploiement Heroku..."
    
    # Créer Procfile
    if [ ! -f "Procfile" ]; then
        echo "web: gunicorn app:app" > Procfile
    fi
    
    # Créer runtime.txt
    if [ ! -f "runtime.txt" ]; then
        python3 --version | sed 's/Python /python-/' > runtime.txt
    fi
    
    log_success "Configuration Heroku créée"
    log_info "Commandes pour déployer sur Heroku:"
    log_info "1. heroku create votre-app-name"
    log_info "2. heroku addons:create heroku-postgresql:mini"
    log_info "3. heroku config:set FLASK_ENV=production"
    log_info "4. git push heroku main"
}

# Optimisations pour la production
optimize_for_production() {
    log_info "Application des optimisations pour la production..."
    
    # Compiler les assets CSS/JS si nécessaire
    if [ -f "static/src" ]; then
        log_info "Compilation des assets..."
        # Ici vous pourriez ajouter la compilation Webpack, Sass, etc.
    fi
    
    # Vérifier la configuration de sécurité
    source venv/bin/activate
    python3 -c "
import os
from config import ProductionConfig

config = ProductionConfig()
issues = []

if not config.SECRET_KEY or config.SECRET_KEY == 'une_cle_secrete_tres_secrete':
    issues.append('❌ SECRET_KEY par défaut détectée')

if not config.SESSION_COOKIE_SECURE:
    issues.append('⚠️  SESSION_COOKIE_SECURE devrait être True en production')

if config.DEBUG:
    issues.append('❌ DEBUG activé en production')

if issues:
    print('Issues de sécurité détectées:')
    for issue in issues:
        print(f'  {issue}')
else:
    print('✅ Configuration de sécurité correcte')
"
    
    log_success "Optimisations appliquées"
}

# Fonction principale
main() {
    echo "🏥 Script de déploiement - Application d'Analyse Médicale"
    echo "========================================================="
    
    # Vérifier les arguments
    case "${1:-full}" in
        "deps")
            install_dependencies
            ;;
        "env")
            setup_environment
            ;;
        "db")
            init_database
            ;;
        "test")
            run_tests
            ;;
        "render")
            deploy_render
            ;;
        "heroku")
            deploy_heroku
            ;;
        "optimize")
            optimize_for_production
            ;;
        "full")
            check_prerequisites
            install_dependencies
            setup_environment
            init_database
            run_tests
            optimize_for_production
            log_success "🎉 Déploiement complet terminé!"
            log_info "Pour démarrer l'application: ./start.sh"
            ;;
        *)
            echo "Usage: $0 [deps|env|db|test|render|heroku|optimize|full]"
            echo ""
            echo "Options:"
            echo "  deps     - Installer les dépendances uniquement"
            echo "  env      - Configurer l'environnement uniquement"
            echo "  db       - Initialiser la base de données uniquement"
            echo "  test     - Exécuter les tests uniquement"
            echo "  render   - Préparer pour Render.com"
            echo "  heroku   - Préparer pour Heroku"
            echo "  optimize - Optimiser pour la production"
            echo "  full     - Déploiement complet (défaut)"
            exit 1
            ;;
    esac
}

# Exécuter la fonction principale avec les arguments
main "$@"
