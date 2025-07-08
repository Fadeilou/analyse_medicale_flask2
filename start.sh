#!/bin/bash

# Script de démarrage pour Render.com
# Configure les variables d'environnement pour OpenCV et PyTorch

export DISPLAY=:99
export QT_QPA_PLATFORM=offscreen
export OMP_NUM_THREADS=1
export TORCH_THREADS=1
export MKL_NUM_THREADS=1

# Initialiser la base de données
python -c "from app import create_database; create_database()"

# Démarrer l'application avec la configuration Gunicorn optimisée
exec gunicorn --config gunicorn.conf.py app:app# Script de démarrage pour Render.com
# Configure les variables d'environnement pour OpenCV

export DISPLAY=:99
export QT_QPA_PLATFORM=offscreen

# Initialiser la base de données
python -c "from app import create_database; create_database()"

# Démarrer l'application avec gunicorn
exec gunicorn --bind 0.0.0.0:$PORT app:app
