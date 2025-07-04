# Configuration Gunicorn optimisée pour Render.com
import os

# Workers et threads
workers = 1  # Un seul worker pour économiser la mémoire
worker_class = "sync"
threads = 2
worker_connections = 1000

# Timeouts augmentés pour le chargement du modèle YOLO
timeout = 300  # 5 minutes pour les requêtes
keepalive = 5
max_requests = 100
max_requests_jitter = 10

# Mémoire
worker_tmp_dir = "/dev/shm"  # Utiliser la RAM pour les fichiers temporaires
preload_app = False  # Ne pas précharger l'app pour éviter les problèmes de mémoire

# Logging
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Bind
bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"

# Graceful timeout pour les modèles ML
graceful_timeout = 120
