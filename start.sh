#!/bin/bash

# Script de démarrage pour Render.com
# Configure les variables d'environnement pour OpenCV

export DISPLAY=:99
export QT_QPA_PLATFORM=offscreen

# Démarrer l'application avec gunicorn
exec gunicorn --bind 0.0.0.0:$PORT app:app
