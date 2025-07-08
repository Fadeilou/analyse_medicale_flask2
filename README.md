# 🏥 Plateforme d'Analyse Médicale - Documentation Complète

## 📋 Vue d'ensemble

Cette plateforme est un système complet d'analyse médicale utilisant l'intelligence artificielle pour l'analyse d'images microscopiques. Elle supporte une architecture multi-rôles (médecins, patients, administrateurs) avec des fonctionnalités avancées de sécurité, d'audit, et de gestion des données.

## 🏗️ Architecture

### Stack Technologique
- **Backend**: Flask (Python 3.12+)
- **Base de données**: PostgreSQL (Supabase)
- **IA**: YOLOv8 (Ultralytics)
- **Frontend**: Bootstrap 5 + JavaScript
- **Déploiement**: Render.com, Heroku, ou VPS

### Structure du Projet
```
analyse_medicale_flask2/
├── app.py                      # Application Flask principale
├── config.py                   # Configuration centralisée
├── models.py                   # Modèles SQLAlchemy
├── routes.py                   # Routes et logique métier
├── forms.py                    # Formulaires WTForms
├── login_form.py              # Formulaires d'authentification
├── annotation_forms.py         # Formulaires pour annotations
├── auth_decorators.py         # Décorateurs d'autorisation
├── notification_service.py    # Service de notifications
├── pdf_service.py             # Génération de PDF
├── export_service.py          # Export de données
├── security_manager.py        # Sécurité avancée (2FA, chiffrement)
├── monitoring.py              # Monitoring et métriques
├── init_db.py                 # Initialisation base de données
├── test_app.py                # Suite de tests
├── deploy.sh                  # Script de déploiement
├── requirements.txt           # Dépendances Python
├── best.pt                    # Modèle IA YOLOv8
├── static/                    # Assets statiques
│   ├── style.css
│   ├── script.js
│   ├── uploaded_images/
│   └── results_images/
├── templates/                 # Templates Jinja2
│   ├── base.html
│   ├── index.html
│   ├── patients_list.html
│   ├── patient_detail.html
│   ├── statistics_dashboard.html
│   ├── notifications.html
│   ├── admin_users.html
│   ├── research_data.html
│   └── errors/
└── migrations/                # Migrations de base de données
```

## 🚀 Installation et Déploiement

### Prérequis
- Python 3.12+
- PostgreSQL (ou Supabase)
- Git

### Installation Rapide
```bash
# Cloner le projet
git clone <repository-url>
cd analyse_medicale_flask2

# Exécuter le script de déploiement
chmod +x deploy.sh
./deploy.sh full
```

### Installation Manuelle
```bash
# 1. Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Configurer l'environnement
cp .env.example .env
# Éditer .env avec vos valeurs

# 4. Initialiser la base de données
python init_db.py

# 5. Démarrer l'application
python app.py
```

### Déploiement Render.com
```bash
./deploy.sh render
```

### Déploiement Heroku
```bash
./deploy.sh heroku
heroku create votre-app-name
heroku addons:create heroku-postgresql:mini
git push heroku main
```

## 👥 Système de Rôles

### Rôles Disponibles

#### 🩺 Médecin (MEDECIN)
**Permissions:**
- Créer, modifier, supprimer des patients
- Effectuer des analyses d'images
- Ajouter des commentaires médicaux
- Voir les statistiques de leurs analyses
- Gérer leurs notifications
- Télécharger des rapports PDF

**Fonctionnalités:**
- Dashboard avec métriques personnelles
- Liste et détail des patients
- Interface d'analyse IA
- Historique des analyses
- Validation/annotation des résultats

#### 🧑‍⚕️ Patient (PATIENT)
**Permissions:**
- Voir leurs propres analyses
- Consulter leurs rapports médicaux
- Recevoir des notifications
- Télécharger leurs rapports PDF

**Fonctionnalités:**
- Profil patient
- Historique médical
- Résultats d'analyses
- Notifications médicales

#### 👤 Administrateur (ADMINISTRATEUR)
**Permissions:**
- Gestion complète des utilisateurs
- Accès aux logs d'audit
- Monitoring système
- Export de données
- Gestion des annotations de recherche
- Configuration système

**Fonctionnalités:**
- Tableau de bord administrateur
- Gestion des utilisateurs
- Audit trail complet
- Métriques système
- Export des données de recherche

## 🤖 Système d'IA

### Modèle YOLOv8
- **Type**: Détection d'objets
- **Classes détectées**: DREPANOCYTES, ELLIPTOCYTES, SCHIZOCYTES, SAINS
- **Seuil de confiance**: 0.4 (configurable)
- **Format de sortie**: Images annotées + données JSON

### Workflow d'Analyse
1. **Upload d'image** par le médecin
2. **Prétraitement** (redimensionnement, normalisation)
3. **Inférence IA** avec le modèle YOLOv8
4. **Post-traitement** des résultats
5. **Génération de l'image annotée**
6. **Sauvegarde** en base de données
7. **Notification** automatique si anomalie critique

### Configuration IA
```python
# Dans config.py
AI_MODEL_PATH = 'best.pt'
AI_CONFIDENCE_THRESHOLD = 0.4
CLASS_NAMES = ["DREPANOCYTES", "ELLIPTOCYTES", "SCHIZOCYTES", "SAINS"]
```

## 🔒 Sécurité

### Authentification
- **Hachage des mots de passe**: bcrypt
- **Sessions sécurisées**: Flask-Login
- **Protection CSRF**: Flask-WTF
- **Contrôle d'accès basé sur les rôles**: Décorateurs personnalisés

### Authentification à Deux Facteurs (2FA)
```python
from security_manager import two_factor_auth

# Activer 2FA pour un utilisateur
secret = two_factor_auth.generate_secret()
qr_code = two_factor_auth.generate_qr_code(user.email, secret)

# Vérifier un token 2FA
is_valid = two_factor_auth.verify_token(secret, user_token)
```

### Chiffrement des Données
```python
from security_manager import security_manager

# Chiffrer des données sensibles
encrypted_data = security_manager.encrypt_data("données sensibles")

# Déchiffrer
decrypted_data = security_manager.decrypt_data(encrypted_data)
```

### Audit Trail
Toutes les actions importantes sont enregistrées :
- Connexions/déconnexions
- Modifications de données patient
- Analyses effectuées
- Accès aux données sensibles

## 📊 Monitoring et Métriques

### Health Checks
```bash
# Vérification de santé
curl http://localhost:5000/monitoring/health

# Métriques détaillées (admin requis)
curl http://localhost:5000/monitoring/metrics
```

### Métriques Collectées
- **Système**: CPU, mémoire, espace disque
- **Base de données**: Connexions, temps de réponse
- **Métier**: Nombre d'analyses, taux de détection, utilisateurs actifs
- **IA**: Statut du modèle, temps d'inférence

### Alertes Automatiques
- Espace disque > 80%
- Mémoire > 90%
- Modèle IA indisponible
- Taux de détection anormal

## 📄 API et Exports

### Formats d'Export Supportés
- **PDF**: Rapports médicaux détaillés
- **CSV**: Données tabulaires pour analyse
- **FHIR/HL7**: Standards médicaux internationaux
- **JSON**: Export complet des données

### Endpoints API Principaux
```python
# Patients
GET    /patients              # Liste des patients
GET    /patients/<id>         # Détail patient
POST   /patients              # Créer patient
PUT    /patients/<id>         # Modifier patient

# Analyses
GET    /analyses              # Liste analyses
POST   /analyses              # Nouvelle analyse
GET    /analyses/<id>/pdf     # Rapport PDF

# Admin
GET    /admin/users           # Gestion utilisateurs
GET    /admin/audit           # Logs d'audit
GET    /admin/export/csv      # Export CSV

# Monitoring
GET    /monitoring/health     # Health check
GET    /monitoring/metrics    # Métriques système
```

## 🧪 Tests

### Exécution des Tests
```bash
# Tests complets
python -m pytest test_app.py -v

# Tests spécifiques
python -m pytest test_app.py::TestUserModel -v

# Coverage
python -m pytest --cov=. test_app.py
```

### Types de Tests
- **Tests unitaires**: Modèles, fonctions utilitaires
- **Tests d'intégration**: Workflows complets
- **Tests API**: Endpoints REST
- **Tests de sécurité**: Authentification, autorisation
- **Tests de performance**: Temps de réponse

## 🔧 Configuration

### Variables d'Environnement
```bash
# .env
FLASK_ENV=production
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:pass@host:port/db

# Email
MAIL_SERVER=smtp.gmail.com
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# IA
AI_MODEL_PATH=best.pt
AI_CONFIDENCE_THRESHOLD=0.4

# Sécurité
SESSION_COOKIE_SECURE=true
```

### Configuration par Environnement
- **Development**: Debug activé, logs verbeux
- **Production**: Sécurité renforcée, logs optimisés
- **Testing**: Base de données en mémoire, CSRF désactivé

## 📚 Utilisation

### Pour les Médecins
1. **Connexion** avec identifiants
2. **Gestion des patients**: Créer/modifier des fiches
3. **Analyse d'images**: Upload et traitement IA
4. **Interprétation**: Ajouter commentaires médicaux
5. **Rapports**: Générer et télécharger des PDF

### Pour les Patients
1. **Connexion** avec identifiants
2. **Consultation**: Voir les résultats d'analyses
3. **Historique**: Accéder à l'historique médical
4. **Téléchargements**: Rapports PDF personnels

### Pour les Administrateurs
1. **Dashboard**: Vue d'ensemble du système
2. **Utilisateurs**: Créer/gérer les comptes
3. **Monitoring**: Surveiller la santé du système
4. **Audit**: Consulter les logs d'activité
5. **Export**: Extraire les données de recherche

## 🚨 Maintenance

### Sauvegardes
```bash
# Sauvegarde base de données
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Sauvegarde fichiers
tar -czf backup_files_$(date +%Y%m%d).tar.gz static/uploaded_images static/results_images
```

### Logs
```bash
# Consulter les logs
tail -f logs/app.log

# Logs d'erreur
tail -f logs/error.log

# Logs de métriques
tail -f logs/metrics.log
```

### Mises à jour
```bash
# Mettre à jour les dépendances
pip install -r requirements.txt --upgrade

# Appliquer les migrations
alembic upgrade head

# Redémarrer l'application
./deploy.sh optimize
```

## 🐛 Dépannage

### Problèmes Courants

#### Modèle IA non chargé
```bash
# Vérifier le fichier modèle
ls -la best.pt

# Vérifier les logs
grep "modèle" logs/app.log
```

#### Erreurs de base de données
```bash
# Test de connexion
python -c "from app import db; print(db.engine.execute('SELECT 1').scalar())"

# Réinitialiser les tables
python init_db.py reset
```

#### Problèmes de permissions
```bash
# Vérifier les dossiers
ls -la static/
chmod 755 static/uploaded_images static/results_images
```

## 📞 Support

### Logs d'Erreur
Les erreurs sont enregistrées dans `logs/app.log` avec les détails suivants :
- Timestamp
- Niveau d'erreur
- Message détaillé
- Stack trace
- Contexte utilisateur

### Monitoring en Temps Réel
- **Health check**: `/monitoring/health`
- **Métriques**: `/monitoring/metrics`
- **Alertes**: `/monitoring/alerts`

### Contact
Pour le support technique, consultez les logs d'audit et les métriques système avant de signaler un problème.

---

## 📝 Notes de Version

### v2.0.0 - Version Complète
- ✅ Architecture multi-rôles complète
- ✅ Sécurité avancée (2FA, chiffrement)
- ✅ Monitoring et métriques
- ✅ Export multi-format
- ✅ Interface responsive
- ✅ Tests complets
- ✅ Documentation complète

### Fonctionnalités Futures
- 🔄 API REST complète
- 🔄 Application mobile
- 🔄 Intelligence artificielle améliorée
- 🔄 Intégration DICOM
- 🔄 Blockchain pour l'intégrité des données
