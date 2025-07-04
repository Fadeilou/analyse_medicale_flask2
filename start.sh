#!/bin/bash

# Script de démarrage pour Render.com
# Configure les variables d'environnement pour OpenCV

export DISPLAY=:99
export QT_QPA_PLATFORM=offscreen

# Initialiser la base de données
python -c "from app import create_database; create_database()"

# Démarrer l'application avec gunicorn
exec gunicorn --bind 0.0.0.0:$PORT app:app
