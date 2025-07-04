# Étape 1: Utiliser une image Python officielle comme base
FROM python:3.12-slim

# Étape 2: Installer les dépendances système nécessaires pour OpenCV
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgcc-s1 \
    && rm -rf /var/lib/apt/lists/*

# Étape 3: Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Étape 3: Copier le fichier des dépendances et les installer
# Copier uniquement requirements.txt d'abord pour profiter du cache Docker
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Étape 4: Copier tout le reste du code de l'application
# Le .dockerignore empêchera la copie des fichiers inutiles
COPY . .

# Étape 5: Exposer le port sur lequel l'application s'exécute
# Assurez-vous que votre application Flask tourne bien sur le port 5000
EXPOSE 5000

# Étape 6: Copier et rendre exécutable le script de démarrage
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Étape 7: Définir la commande pour lancer l'application
CMD ["/app/start.sh"]
