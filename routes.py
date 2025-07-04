from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory, current_app
import os
import uuid # Pour générer des noms de fichiers uniques
from werkzeug.utils import secure_filename
from models import db, User, Patient, AnalyseResult
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date
from forms import RegistrationForm
from login_form import LoginForm, ForgotPasswordForm, ResetPasswordForm
import secrets
import string
import cv2
import numpy as np
import traceback
# Supprimer les imports liés à TensorFlow/Keras si AlexNet n'est plus utilisé
# import tensorflow as tf
# from tensorflow.keras.preprocessing import image
# from tensorflow.keras.models import Sequential, load_model
# from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Activation, Dropout, ZeroPadding2D, BatchNormalization
import pdb # Gardé si vous l'utilisez pour le débogage

# --- Importer le modèle d'IA ---
from ultralytics import YOLO

routes = Blueprint('routes', __name__)

UPLOAD_FOLDER = 'static/uploaded_images'
# --- Dossier pour les images résultat avec masques ---
RESULTS_FOLDER = 'static/results_images'
ALLOWED_EXTENSIONS_IMAGES = {'png', 'jpg', 'jpeg'}

# --- Configuration du modèle d'IA ---
# --- !!! METTEZ ICI LE CHEMIN VERS VOTRE MODÈLE .pt !!! ---
MODEL_PATH = 'best.pt' # ou 'models/best.pt' etc.
CONFIDENCE_THRESHOLD = 0.4 # Seuil de confiance pour les détections
CLASS_NAMES = ["DREPANOCYTES", "ELLIPTOCYTES", "SCHIZOCYTES", "SAINS"] # Ajout de la classe SAINS

# --- Chargement du modèle d'IA (variable globale) ---
ai_model = None
model_loaded = False

def load_ai_model():
    global ai_model, model_loaded
    if model_loaded:
        return ai_model
        
    try:
        # Créer le dossier de résultats s'il n'existe pas
        if not os.path.exists(RESULTS_FOLDER):
            os.makedirs(RESULTS_FOLDER)
            print(f"Dossier de résultats créé: {RESULTS_FOLDER}")

        if os.path.exists(MODEL_PATH):
            print("Chargement du modèle d'IA en cours...")
            # Charger avec des paramètres optimisés pour Render.com
            ai_model = YOLO(MODEL_PATH)
            
            # Désactiver la fusion des couches pour économiser la mémoire
            if hasattr(ai_model.model, 'fuse'):
                try:
                    # Éviter la fusion automatique qui peut causer des erreurs de mémoire
                    pass  # Ne pas appeler fuse() automatiquement
                except Exception as e:
                    print(f"Warning: Impossible de fusionner le modèle: {e}")
            
            model_loaded = True
            print(f"Modèle d'IA chargé avec succès depuis: {MODEL_PATH}")
        else:
            print(f"ERREUR: Fichier modèle d'IA non trouvé à l'emplacement: {MODEL_PATH}")
            ai_model = None
            model_loaded = False
    except Exception as e:
        print(f"Erreur lors du chargement du modèle d'IA: {e}")
        ai_model = None
        model_loaded = False
        
    return ai_model

# Charger le modèle d'IA seulement au premier usage (chargement paresseux)
# load_ai_model()

# --- Supprimer ou commenter l'ancien chargement du modèle CNN ---
# model_cnn = None
# def load_cnn_model(): ...
# load_cnn_model()
# def create_alexnet_model(...): ...
# -----------------------------------------------------------

# Function to verify if the file is an allowed image file
def allowed_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_IMAGES

# --- Landing Page ---
@routes.route('/landing')
def landing():
    return render_template('landing.html')

# --- Route principale pour rediriger vers la landing page si non connecté ---
@routes.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('routes.dashboard'))
    return redirect(url_for('routes.landing'))

# --- Authentification (modifié pour gérer remember_me) ---
@routes.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: 
        return redirect(url_for('routes.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember_me.data)
            flash('Connexion réussie! Bienvenue sur MediScan.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('routes.dashboard'))
        else: 
            flash('Nom d\'utilisateur ou mot de passe incorrect. Veuillez réessayer.', 'danger')
    return render_template('login.html', title='Connexion', form=form, logged_out_content=True)

@routes.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('routes.dashboard'))
    
    try:
        form = RegistrationForm()
        print(f"DEBUG: Form created successfully: {form}")
        
        if form.validate_on_submit():
            hashed_password = generate_password_hash(form.password.data)
            user = User(username=form.username.data, password=hashed_password)
            db.session.add(user)
            db.session.commit()
            flash('Compte créé avec succès! Bienvenue dans la communauté MediScan.', 'success')
            flash('Vous pouvez maintenant vous connecter avec vos identifiants.', 'info')
            return redirect(url_for('routes.login'))
        
        print(f"DEBUG: About to render template with form: {form}")
        print(f"DEBUG: Form errors: {form.errors}")
        return render_template('register_minimal.html', title='Inscription', form=form, logged_out_content=True)
        
    except Exception as e:
        print(f"ERROR in register route: {str(e)}")
        print(f"ERROR traceback: {traceback.format_exc()}")
        return f"Error: {str(e)}", 500

@routes.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Déconnexion réussie. À bientôt sur MediScan !', 'info')
    return redirect(url_for('routes.landing'))

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

# --- Route Page d'Analyse (MODIFIÉE pour l'IA) ---
@routes.route('/analyse', methods=['GET', 'POST'])
@login_required
def analyse():
    resultat_analyse = None
    patient_info = {}
    image_filename_result = None # Nom du fichier image RÉSULTAT (avec masques)

    if request.method == 'POST':
        # Vérifier si le modèle peut être chargé
        try:
            if ai_model is None:
                print("Tentative de chargement du modèle...")
                load_ai_model()
                if ai_model is None:
                    flash("Erreur: Le modèle d'analyse d'IA n'est pas disponible. Veuillez réessayer dans quelques instants.", 'danger')
                    return render_template('index.html', title='Analyse', dashboard_content=True)
        except Exception as e:
            flash(f"Erreur de chargement du modèle: {str(e)}", 'danger')
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

                    # --- Analyse de l'image avec l'IA ---
                    resultat_analyse = analyse_image_ai(file_content, original_filename)
                    image_filename_result = resultat_analyse.get('output_image_filename') # Récupère nom fichier résultat

                    # Optionnel: Sauvegarder l'image originale si besoin (non nécessaire pour l'analyse elle-même)
                    # original_image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], original_filename)
                    # with open(original_image_path, 'wb') as f:
                    #     f.write(file_content)

                except Exception as e:
                    error_msg = str(e)
                    if "WORKER TIMEOUT" in error_msg or "out of memory" in error_msg.lower():
                        flash("Erreur: Ressources insuffisantes pour traiter cette image. Veuillez essayer avec une image plus petite.", 'danger')
                    elif "torch" in error_msg.lower() or "cuda" in error_msg.lower():
                        flash("Erreur: Problème de configuration du modèle. Veuillez réessayer.", 'danger')
                    else:
                        flash(f"Erreur lors de l'analyse de l'image: {error_msg}", 'danger')
                    print(f"Traceback de l'erreur d'analyse: {traceback.format_exc()}")
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


def analyse_image_ai(image_file_content, original_filename):
    global ai_model
    
    # Chargement paresseux du modèle
    if ai_model is None:
        print("Chargement du modèle d'IA à la demande...")
        ai_model = load_ai_model()
        if ai_model is None:
            raise Exception("Le modèle d'IA n'a pas pu être chargé.")

    try:
        # Décoder l'image depuis les bytes
        nparr = np.frombuffer(image_file_content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Impossible de décoder l'image.")

        # Redimensionner l'image pour économiser la mémoire si elle est trop grande
        height, width = img.shape[:2]
        max_size = 1024  # Taille maximale recommandée pour Render.com
        if max(height, width) > max_size:
            scale = max_size / max(height, width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
            print(f"Image redimensionnée de {width}x{height} à {new_width}x{new_height}")

        # Exécuter l'inférence avec des paramètres optimisés
        print("Début de l'inférence...")
        results = ai_model.predict(
            img, 
            conf=CONFIDENCE_THRESHOLD, 
            verbose=False,
            device='cpu',  # Forcer l'utilisation du CPU sur Render.com
            imgsz=640      # Taille d'image optimisée
        )
        print("Inférence terminée.")

        num_detections = 0
        detected_diseases = set()
        output_img_array = img.copy() # Commencer avec l'image originale

        if results and hasattr(results[0], 'masks') and results[0].masks is not None:
            num_detections = len(results[0].boxes)
            if num_detections > 0:
                # Récupérer les classes détectées d'abord pour déterminer le statut
                for box in results[0].boxes:
                    class_id = int(box.cls.item())
                    if 0 <= class_id < len(CLASS_NAMES):
                        disease_name = CLASS_NAMES[class_id]
                        detected_diseases.add(disease_name)
                    else:
                        print(f"Warning: Invalid class_id {class_id} detected in results.")

        # Déterminer le statut et la recommandation
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
            # Pour les patients sains, garder l'image originale sans masques
            output_img_array = img.copy()
        else:
            # Seulement des maladies détectées - appliquer les masques
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
            
            # Appliquer les masques seulement pour les malades
            if results and hasattr(results[0], 'masks') and results[0].masks is not None and num_detections > 0:
                output_img_array = results[0].plot(
                    boxes=False,   # Ne pas dessiner les rectangles
                    labels=False,  # Ne pas dessiner les textes (classe + confiance)
                    masks=True     # Dessiner les masques
                )


        # Sauvegarder l'image résultat
        # Pour les patients sains: image originale
        # Pour les patients malades: image avec masques
        base, ext = os.path.splitext(original_filename)
        unique_id = uuid.uuid4().hex[:8]
        output_filename = f"result_{base}_{unique_id}{ext}"
        output_image_path = os.path.join(current_app.config['RESULTS_FOLDER'], output_filename)

        try:
            cv2.imwrite(output_image_path, output_img_array)
            if final_status == "Sain":
                print(f"Image résultat (originale) sauvegardée dans: {output_image_path}")
            else:
                print(f"Image résultat (avec masques) sauvegardée dans: {output_image_path}")
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
        print(f"Erreur dans analyse_image_ai: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise Exception(f"Erreur interne lors de l'analyse: {e}")

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
            # --- Récupérer infos de l'analyse d'IA ---
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

# --- Route mot de passe oublié ---
@routes.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('routes.dashboard'))
    
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            # Générer un mot de passe temporaire
            temp_password = generate_temp_password()
            user.password = generate_password_hash(temp_password)
            db.session.commit()
            
            # Stocker le mot de passe temporaire en session pour l'afficher
            session['temp_password'] = temp_password
            session['username'] = user.username
            
            flash(f'Un mot de passe temporaire a été généré: {temp_password}', 'success')
            flash('Connectez-vous avec ce mot de passe temporaire et changez-le immédiatement.', 'info')
            return redirect(url_for('routes.reset_password'))
        else:
            flash('Aucun compte trouvé avec ce nom d\'utilisateur.', 'danger')
    
    return render_template('forgot_password.html', title='Mot de passe oublié', form=form)

# --- Route pour changer le mot de passe ---
@routes.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    # Vérifier si l'utilisateur a le droit d'accéder à cette page
    if 'temp_password' not in session and not current_user.is_authenticated:
        flash('Accès non autorisé. Veuillez d\'abord demander une réinitialisation.', 'danger')
        return redirect(url_for('routes.forgot_password'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        if 'username' in session:
            # Réinitialisation après mot de passe oublié
            user = User.query.filter_by(username=session['username']).first()
            if user:
                user.password = generate_password_hash(form.new_password.data)
                db.session.commit()
                
                # Nettoyer la session
                session.pop('temp_password', None)
                session.pop('username', None)
                
                flash('Votre mot de passe a été mis à jour avec succès!', 'success')
                flash('Vous pouvez maintenant vous connecter avec votre nouveau mot de passe.', 'info')
                return redirect(url_for('routes.login'))
        elif current_user.is_authenticated:
            # Changement de mot de passe depuis le profil
            current_user.password = generate_password_hash(form.new_password.data)
            db.session.commit()
            flash('Votre mot de passe a été mis à jour avec succès!', 'success')
            return redirect(url_for('routes.profile'))
    
    return render_template('reset_password.html', title='Nouveau mot de passe', form=form)

def generate_temp_password(length=12):
    """Génère un mot de passe temporaire sécurisé"""
    characters = string.ascii_letters + string.digits + "!@#$%&*"
    temp_password = ''.join(secrets.choice(characters) for _ in range(length))
    return temp_password