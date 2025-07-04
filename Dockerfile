# Étape 1: Utiliser une image Python officielle comme base
FROM python:3.12-slim

# Étape 2: Définir le répertoire de travail dans le conteneur
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

# Étape 6: Définir la commande pour lancer l'application
# Utilisation de gunicorn pour un serveur de production plus robuste que le serveur de dev de Flask
# Vous devrez peut-être ajouter 'gunicorn' à votre requirements.txt
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
