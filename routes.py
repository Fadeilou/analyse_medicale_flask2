from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory, current_app
import os
import uuid # Pour générer des noms de fichiers uniques
from werkzeug.utils import secure_filename
from models import db, User, Patient, AnalyseResult
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date
from forms import RegistrationForm
from login_form import LoginForm
import cv2
import numpy as np
import traceback
# Supprimer les imports liés à TensorFlow/Keras si AlexNet n'est plus utilisé
# import tensorflow as tf
# from tensorflow.keras.preprocessing import image
# from tensorflow.keras.models import Sequential, load_model
# from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Activation, Dropout, ZeroPadding2D, BatchNormalization
import pdb # Gardé si vous l'utilisez pour le débogage

# --- NOUVEAU: Importer YOLO ---
from ultralytics import YOLO

routes = Blueprint('routes', __name__)

UPLOAD_FOLDER = 'static/uploaded_images'
# --- NOUVEAU: Dossier pour les images résultat avec masques ---
RESULTS_FOLDER = 'static/results_images'
ALLOWED_EXTENSIONS_IMAGES = {'png', 'jpg', 'jpeg'}

# --- NOUVEAU: Configuration YOLOv8 ---
# --- !!! METTEZ ICI LE CHEMIN VERS VOTRE MODÈLE .pt !!! ---
YOLO_MODEL_PATH = 'best.pt' # ou 'models/best.pt' etc.
CONFIDENCE_THRESHOLD_YOLO = 0.4 # Seuil de confiance pour les détections YOLO
CLASS_NAMES_YOLO = ["DREPANOCYTES", "ELLIPTOCYTES", "SCHIZOCYTES", "SAINS"] # Ajout de la classe SAINS

# --- NOUVEAU: Chargement du modèle YOLOv8 (variable globale) ---
model_yolo = None
def load_yolo_model():
    global model_yolo
    try:
        # Créer le dossier de résultats s'il n'existe pas
        if not os.path.exists(RESULTS_FOLDER):
            os.makedirs(RESULTS_FOLDER)
            print(f"Dossier de résultats créé: {RESULTS_FOLDER}")

        if os.path.exists(YOLO_MODEL_PATH):
            model_yolo = YOLO(YOLO_MODEL_PATH)
            # Vous pouvez optionnellement faire une inférence rapide pour "chauffer" le modèle si nécessaire
            # model_yolo.predict(np.zeros((640, 640, 3)), verbose=False)
            print(f"Modèle YOLOv8 chargé avec succès depuis: {YOLO_MODEL_PATH}")
        else:
            print(f"ERREUR: Fichier modèle YOLOv8 non trouvé à l'emplacement: {YOLO_MODEL_PATH}")
            model_yolo = None
    except Exception as e:
        print(f"Erreur lors du chargement du modèle YOLOv8: {e}")
        model_yolo = None

# Charger le modèle YOLO au démarrage
load_yolo_model()

# --- Supprimer ou commenter l'ancien chargement du modèle CNN ---
# model_cnn = None
# def load_cnn_model(): ...
# load_cnn_model()
# def create_alexnet_model(...): ...
# -----------------------------------------------------------

# Function to verify if the file is an allowed image file
def allowed_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_IMAGES

# --- Authentification (inchangé) ---
@routes.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('routes.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user); flash('Connexion réussie!', 'success'); return redirect(url_for('routes.dashboard'))
        else: flash('Login incorrect.', 'danger')
    return render_template('login.html', title='Connexion', form=form, logged_out_content=True)

@routes.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('routes.dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        user = User(username=form.username.data, password=hashed_password)
        db.session.add(user); db.session.commit()
        flash('Compte créé avec succès!', 'success'); return redirect(url_for('routes.login'))
    return render_template('register.html', title='Inscription', form=form, logged_out_content=True)

@routes.route('/logout')
@login_required
def logout():
    logout_user(); flash('Déconnexion réussie.', 'info'); return redirect(url_for('routes.login'))

@routes.route('/profile')
@login_required
def profile():
    # Pour l'instant, rend juste le template
    # Vous pourrez ajouter la logique pour récupérer/modifier les infos plus tard
    return render_template('profile.html', title='Profil Utilisateur', dashboard_content=True)


# --- Dashboard Routes (inchangé) ---
@routes.route('/dashboard')
@login_required
def dashboard():
    return render_template('index.html', title='Tableau de Bord - Analyse', dashboard_content=True)

@routes.route('/')
@login_required
def index_redirect_dashboard():
    return redirect(url_for('routes.dashboard'))

@routes.route('/analyses')
@login_required
def analyses_list():
    analyses = AnalyseResult.query.filter_by(user_id=current_user.id).order_by(AnalyseResult.date_analyse.desc()).all()
    return render_template('analyses_list.html', analyses=analyses, title='Liste des Analyses', dashboard_content=True)

# --- Route Page de Détail de l'Analyse (Peut nécessiter ajustement pour afficher l'image résultat) ---
@routes.route('/analyse_detail/<int:analyse_id>')
@login_required
def analyse_detail_page(analyse_id):
    analyse = AnalyseResult.query.get_or_404(analyse_id)
    if analyse.user_id != current_user.id:
        flash("Accès non autorisé.", 'danger')
        return redirect(url_for('routes.analyses_list'))
    # Le template 'analyse_detail.html' devra utiliser analyse.image_path pour l'image
    return render_template('analyse_detail.html', analyse=analyse, title=f"Détail Analyse #{analyse.id}")

# --- Route Page d'Analyse (MODIFIÉE pour YOLOv8) ---
@routes.route('/analyse', methods=['GET', 'POST'])
@login_required
def analyse():
    resultat_analyse = None
    patient_info = {}
    image_filename_result = None # Nom du fichier image RÉSULTAT (avec masques)

    if request.method == 'POST':
        if model_yolo is None:
            flash("Erreur: Le modèle d'analyse YOLOv8 n'est pas chargé.", 'danger')
            return render_template('index.html', title='Analyse', dashboard_content=True)

        if 'image_upload' not in request.files:
            flash('Aucun fichier image sélectionné.', 'warning')
        else:
            image_file = request.files['image_upload']
            if image_file.filename == '':
                flash('Aucun fichier image sélectionné.', 'warning')
            elif allowed_image_file(image_file.filename):
                try:
                    # Lire le contenu pour l'analyse et pour une sauvegarde potentielle
                    file_content = image_file.read()
                    original_filename = secure_filename(image_file.filename)

                    # --- NOUVEAU: Analyse de l'image avec YOLOv8 ---
                    resultat_analyse = analyse_image_yolo(file_content, original_filename)
                    image_filename_result = resultat_analyse.get('output_image_filename') # Récupère nom fichier résultat

                    # Optionnel: Sauvegarder l'image originale si besoin (non nécessaire pour l'analyse elle-même)
                    # original_image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], original_filename)
                    # with open(original_image_path, 'wb') as f:
                    #     f.write(file_content)

                except Exception as e:
                    flash(f"Erreur lors de l'analyse de l'image: {e}", 'danger')
                    print(f"Traceback de l'erreur d'analyse: {traceback.format_exc()}") # Log détaillé
                    resultat_analyse = None
                    image_filename_result = None
            else:
                flash('Type de fichier non autorisé.', 'danger')

    # Passe le nom du fichier *résultat* au template
    return render_template('index.html',
                           resultat_analyse=resultat_analyse,
                           patient_info=patient_info,
                           title='Analyse',
                           dashboard_content=True,
                           image_filename=image_filename_result) # Utilise image_filename_result ici


def analyse_image_yolo(image_file_content, original_filename):
    global model_yolo
    if model_yolo is None:
        raise Exception("Le modèle YOLOv8 n'est pas chargé.")

    try:
        # Décoder l'image depuis les bytes
        nparr = np.frombuffer(image_file_content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Impossible de décoder l'image.")

        # Exécuter l'inférence YOLOv8
        results = model_yolo.predict(img, conf=CONFIDENCE_THRESHOLD_YOLO, verbose=False)

        num_detections = 0
        detected_diseases = set()
        output_img_array = img.copy() # Commencer avec l'image originale

        if results and hasattr(results[0], 'masks') and results[0].masks is not None:
            num_detections = len(results[0].boxes)
            if num_detections > 0:
                # --- MODIFICATION ICI ---
                # Utiliser plot() en désactivant les boîtes et les labels
                output_img_array = results[0].plot(
                    boxes=False,   # Ne pas dessiner les rectangles
                    labels=False,  # Ne pas dessiner les textes (classe + confiance)
                    masks=True     # Dessiner les masques (par défaut mais explicite)
                    # Vous pouvez garder d'autres paramètres de style si vous le souhaitez
                    # line_width=..., mask_alpha=..., etc.
                )
                # -----------------------

                # Récupérer les classes détectées (la logique reste la même)
                for box in results[0].boxes:
                    class_id = int(box.cls.item())
                    if 0 <= class_id < len(CLASS_NAMES_YOLO):
                        disease_name = CLASS_NAMES_YOLO[class_id]
                        detected_diseases.add(disease_name)
                    else:
                        print(f"Warning: Invalid class_id {class_id} detected in YOLO results.")

        # Déterminer le statut et la recommandation (NOUVELLE LOGIQUE)
        if num_detections == 0:
            # Aucune détection du tout - cas d'erreur ou image non analysable
            final_status = "Indéterminé"
            recommandation = "Aucune cellule détectée. Veuillez vérifier la qualité de l'image."
            detected_diseases_list = []
        elif "SAINS" in detected_diseases:
            # Classe SAINS détectée - priorité donnée au statut sain même si d'autres classes sont présentes
            final_status = "Sain"
            recommandation = "Cellules saines détectées. Test négatif."
            detected_diseases_list = ["SAINS"]
        else:
            # Seulement des maladies détectées
            final_status = "Malade"
            detected_diseases_list = sorted(list(detected_diseases))
            reco_parts = []
            if "DREPANOCYTES" in detected_diseases_list: 
                reco_parts.append("Présence de drépanocytes. Électrophorèse de l'hémoglobine suggérée.")
            if "ELLIPTOCYTES" in detected_diseases_list: 
                reco_parts.append("Présence d'elliptocytes. Examens complémentaires nécessaires.")
            if "SCHIZOCYTES" in detected_diseases_list: 
                reco_parts.append("Présence de schizocytes. Examens complémentaires nécessaires.")
            if not reco_parts: 
                reco_parts.append("Cellules anormales détectées. Examen médical requis.")
            recommandation = " ".join(reco_parts)


        # Sauvegarder l'image résultat (avec seulement les masques maintenant)
        # ... (logique de sauvegarde inchangée) ...
        base, ext = os.path.splitext(original_filename)
        unique_id = uuid.uuid4().hex[:8]
        output_filename = f"result_{base}_{unique_id}{ext}"
        output_image_path = os.path.join(current_app.config['RESULTS_FOLDER'], output_filename)

        try:
            # Important: output_img_array contient maintenant l'image AVEC seulement les masques
            cv2.imwrite(output_image_path, output_img_array)
            print(f"Image résultat (masques seulement) sauvegardée dans: {output_image_path}")
        except Exception as e_save:
            print(f"ERREUR lors de la sauvegarde de l'image résultat {output_filename}: {e_save}")
            output_filename = None


        return {
            "status": final_status,
            "diseases": detected_diseases_list,
            "recommandation": recommandation,
            "output_image_filename": output_filename
        }

    except Exception as e:
        print(f"Erreur dans analyse_image_yolo: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise Exception(f"Erreur interne lors de l'analyse YOLOv8: {e}")

# --- Supprimer l'ancienne fonction analyse_image CNN ---
# def analyse_image(image_file): ...
# -----------------------------------------------------

# --- Fonctions allowed_file (inchangé) ---
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Route pour la sauvegarde (MODIFIÉE) ---
@routes.route('/save_analysis', methods=['POST'])
@login_required
def save_analysis():
    if request.method == 'POST':
        try:
            patient_nom = request.form['patient_nom']
            patient_prenom = request.form['patient_prenom']
            patient_date_naissance_str = request.form['patient_date_naissance']
            # --- NOUVEAU: Récupérer infos de l'analyse YOLO ---
            output_image_filename = request.form['output_image_filename'] # Nom fichier résultat
            status = request.form['status'] # "Sain" ou "Malade"
            diseases_str = request.form['diseases'] # String séparée par des virgules
            recommandation = request.form['recommandation']

            patient_date_naissance = date.fromisoformat(patient_date_naissance_str) if patient_date_naissance_str else None
            test_positif = (status == 'Malade')
            # Type anomalie: stocker la liste jointe par des virgules
            type_anomalie_db = diseases_str if test_positif else None

            patient = Patient(nom=patient_nom, prenom=patient_prenom, date_naissance=patient_date_naissance)
            db.session.add(patient)
            db.session.flush() # Pour obtenir patient.id avant commit
            patient_id = patient.id

            # --- Chemin de l'image résultat pour la DB ---
            # Le chemin doit être relatif au dossier 'static' pour l'affichage HTML
            image_path_db = os.path.join('results_images', output_image_filename)

            analyse_result = AnalyseResult(
                image_path=image_path_db, # Chemin vers l'image RÉSULTAT
                test_positif=test_positif,
                type_anomalie=type_anomalie_db, # Stocke la liste comme string
                recommandation=recommandation,
                patient_id=patient_id,
                user_id=current_user.id,
                image_filename=output_image_filename # Optionnel, garder si utile ailleurs
            )
            db.session.add(analyse_result)
            db.session.commit()

            flash('Résultats sauvegardés avec succès!', 'success')
            return redirect(url_for('routes.analyses_list'))

        except Exception as e:
             db.session.rollback() # Annuler les changements en cas d'erreur
             flash(f"Erreur lors de la sauvegarde de l'analyse: {e}", 'danger')
             print(f"Erreur sauvegarde: {traceback.format_exc()}")
             # Rediriger vers la page d'analyse précédente pourrait être utile ici,
             # mais nécessite de repasser les données. Pour l'instant, redirection simple.
             return redirect(url_for('routes.dashboard')) # Ou routes.analyse?

    return redirect(url_for('routes.dashboard'))

# --- NOUVEAU: Route pour servir les images résultat ---
@routes.route('/results_images/<filename>')
def send_result_image(filename):
    # Attention: Ne pas utiliser dans un environnement de production sans sécurisation
    # C'est juste pour que le template puisse afficher l'image depuis static/results_images
    try:
        # Utiliser current_app pour accéder à la configuration
        results_folder_abs = os.path.join(current_app.root_path, RESULTS_FOLDER)
        return send_from_directory(results_folder_abs, filename)
    except FileNotFoundError:
        # Gérer le cas où l'image n'est pas trouvée
        return "Image non trouvée", 404
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'image résultat {filename}: {e}")
        return "Erreur serveur", 500