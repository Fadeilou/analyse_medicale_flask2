from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory, current_app, send_file
import os
import uuid # Pour générer des noms de fichiers uniques
from werkzeug.utils import secure_filename
from models import db, User, Patient, AnalyseResult, RoleEnum, Notification, AuditLog, Annotation
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date, datetime, timedelta, timezone
from forms import RegistrationForm
from login_form import LoginForm, ForgotPasswordForm, ResetPasswordForm
from annotation_forms import AnnotationForm, PatientForm, CommentForm, UserForm, BulkAnnotationForm
from auth_decorators import medecin_required, admin_required, require_role, log_user_activity, audit_action
from notification_service import notification_service
from pdf_service import pdf_service
from export_service import export_service
import secrets
import string
import cv2
import numpy as np
import traceback
from sqlalchemy import func, and_, or_, desc

def utcnow():
    """Timezone-aware UTC now function"""
    return datetime.now(timezone.utc)

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
            flash('Connexion réussie! Bienvenue sur DiseaseDetect.', 'success')
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
            flash('Compte créé avec succès! Bienvenue dans la communauté DiseaseDetect.', 'success')
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
    flash('Déconnexion réussie. À bientôt sur DiseaseDetect !', 'info')
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

# --- Route Page d'Analyse (RESTREINTE AUX MÉDECINS) ---
@routes.route('/analyse', methods=['GET', 'POST'])
@routes.route('/analyse/<int:patient_id>', methods=['GET', 'POST'])
@login_required
@medecin_required
def analyse(patient_id=None):
    resultat_analyse = None
    patient_info = {}
    image_filename_result = None
    
    # Si un patient_id est fourni, récupérer les infos du patient
    selected_patient = None
    if patient_id:
        selected_patient = Patient.query.get_or_404(patient_id)
        patient_info = {
            'nom': selected_patient.nom,
            'prenom': selected_patient.prenom,
            'date_naissance': selected_patient.date_naissance.strftime('%Y-%m-%d') if selected_patient.date_naissance else '',
            'id': selected_patient.id
        }

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
                    # Lire le contenu pour l'analyse
                    file_content = image_file.read()
                    original_filename = secure_filename(image_file.filename)

                    # --- Analyse de l'image avec l'IA ---
                    resultat_analyse = analyse_image_ai(file_content, original_filename)
                    image_filename_result = resultat_analyse.get('output_image_filename')

                    # Enregistrer l'activité
                    log_user_activity('ANALYSE_IMAGE', 'AnalyseResult', details={
                        'filename': original_filename,
                        'status': resultat_analyse.get('status')
                    })

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

    return render_template('index.html',
                           resultat_analyse=resultat_analyse,
                           patient_info=patient_info,
                           title='Analyse',
                           dashboard_content=True,
                           image_filename=image_filename_result)


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
            existing_patient_id = request.form.get('existing_patient_id')  # Nouveau champ
            
            # --- Récupérer infos de l'analyse d'IA ---
            output_image_filename = request.form['output_image_filename'] # Nom fichier résultat
            status = request.form['status'] # "Sain" ou "Malade"
            diseases_str = request.form['diseases'] # String séparée par des virgules
            recommandation = request.form['recommandation']

            patient_date_naissance = date.fromisoformat(patient_date_naissance_str) if patient_date_naissance_str else None
            test_positif = (status == 'Malade')
            # Type anomalie: stocker la liste jointe par des virgules
            type_anomalie_db = diseases_str if test_positif else None

            # Utiliser patient existant ou créer un nouveau
            if existing_patient_id:
                # Utiliser le patient existant
                patient = Patient.query.get(int(existing_patient_id))
                if not patient:
                    flash('Patient introuvable.', 'danger')
                    return redirect(url_for('routes.analyse'))
                patient_id = patient.id
            else:
                # Créer un nouveau patient
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

# --- NOUVELLES ROUTES POUR LES FONCTIONNALITÉS AVANCÉES ---

# ============================================================================
# GESTION DES PATIENTS (MÉDECINS SEULEMENT)
# ============================================================================

@routes.route('/patients')
@login_required
@medecin_required
@audit_action('VIEW', 'Patient')
def patients_list():
    """Liste paginée des patients avec recherche"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    
    query = Patient.query
    
    if search:
        query = query.filter(
            or_(
                Patient.nom.contains(search),
                Patient.prenom.contains(search),
                Patient.numero_securite_sociale.contains(search),
                Patient.email.contains(search)
            )
        )
    
    patients = query.paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Statistiques rapides
    stats = {
        'analyses_today': AnalyseResult.query.filter(
            func.date(AnalyseResult.created_at) == date.today()
        ).count(),
        'anomalies_today': AnalyseResult.query.filter(
            and_(
                func.date(AnalyseResult.created_at) == date.today(),
                AnalyseResult.type_anomalie.isnot(None)
            )
        ).count(),
        'pending_reviews': AnalyseResult.query.filter(
            AnalyseResult.commentaire_medecin.is_(None)
        ).count()
    }
    
    return render_template('patients_list.html',
                         patients=patients,
                         stats=stats,
                         title='Gestion des Patients',
                         dashboard_content=True)

@routes.route('/patients/<int:patient_id>')
@login_required
@medecin_required
@audit_action('VIEW', 'Patient')
def patient_detail(patient_id):
    """Détails d'un patient avec historique des analyses"""
    patient = Patient.query.get_or_404(patient_id)
    
    # Ordonner les analyses par date décroissante
    analyses = AnalyseResult.query.filter_by(patient_id=patient_id)\
                                  .order_by(desc(AnalyseResult.created_at))\
                                  .all()
    
    return render_template('patient_detail.html',
                         patient=patient,
                         analyses=analyses,
                         title=f'Patient: {patient.nom} {patient.prenom}',
                         dashboard_content=True)

@routes.route('/patients/create', methods=['GET', 'POST'])
@login_required
@medecin_required
@audit_action('CREATE', 'Patient')
def create_patient():
    """Créer un nouveau patient"""
    form = PatientForm()
    
    if form.validate_on_submit():
        try:
            # Convertir la date de naissance
            date_naissance = None
            if form.date_naissance.data:
                try:
                    date_naissance = datetime.strptime(form.date_naissance.data, '%d/%m/%Y').date()
                except ValueError:
                    flash('Format de date invalide. Utilisez JJ/MM/AAAA', 'danger')
                    return render_template('patient_form.html', form=form, 
                                         title='Nouveau Patient', dashboard_content=True)
            
            patient = Patient(
                nom=form.nom.data,
                prenom=form.prenom.data,
                date_naissance=date_naissance,
                sexe=form.sexe.data if form.sexe.data else None,
                numero_securite_sociale=form.numero_securite_sociale.data,
                email=form.email.data,
                telephone=form.telephone.data,
                adresse=form.adresse.data,
                medecin_traitant=form.medecin_traitant.data,
                groupe_sanguin=form.groupe_sanguin.data if hasattr(form, 'groupe_sanguin') and form.groupe_sanguin.data else None,
                allergies=form.allergies.data if hasattr(form, 'allergies') else None,
                antecedents_medicaux=form.antecedents_medicaux.data if hasattr(form, 'antecedents_medicaux') else None
            )
            
            db.session.add(patient)
            db.session.commit()
            
            # Notification
            notification_service.create_notification(
                user_id=current_user.id,
                titre="Nouveau patient créé",
                message=f"Le patient {patient.nom} {patient.prenom} a été ajouté au système",
                type="patient_registered"
            )
            
            flash('Patient créé avec succès!', 'success')
            return redirect(url_for('routes.patient_detail', patient_id=patient.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la création du patient: {e}', 'danger')
    
    return render_template('patient_form.html',
                         form=form,
                         title='Nouveau Patient',
                         dashboard_content=True)

@routes.route('/patients/<int:patient_id>/edit', methods=['GET', 'POST'])
@login_required
@medecin_required
@audit_action('UPDATE', 'Patient')
def edit_patient(patient_id):
    """Modifier un patient existant"""
    patient = Patient.query.get_or_404(patient_id)
    form = PatientForm(obj=patient)
    
    # Pré-remplir la date de naissance au bon format
    if patient.date_naissance:
        form.date_naissance.data = patient.date_naissance.strftime('%d/%m/%Y')
    
    if form.validate_on_submit():
        try:
            # Convertir la date de naissance AVANT populate_obj
            date_naissance_converted = None
            if form.date_naissance.data:
                try:
                    date_naissance_converted = datetime.strptime(form.date_naissance.data, '%d/%m/%Y').date()
                except ValueError:
                    flash('Format de date invalide. Utilisez JJ/MM/AAAA', 'danger')
                    return render_template('patient_form.html', form=form, patient=patient,
                                         title='Modifier Patient', dashboard_content=True)
            
            # Copier toutes les données du formulaire sauf date_naissance
            patient.nom = form.nom.data
            patient.prenom = form.prenom.data
            patient.sexe = form.sexe.data
            patient.telephone = form.telephone.data
            patient.email = form.email.data
            patient.adresse = form.adresse.data
            patient.antecedents_medicaux = form.antecedents_medicaux.data
            patient.allergies = form.allergies.data
            patient.medecin_traitant = form.medecin_traitant.data
            
            # Assigner la date convertie
            if date_naissance_converted:
                patient.date_naissance = date_naissance_converted
            
            patient.date_modification = utcnow()
            
            db.session.commit()
            flash('Patient modifié avec succès!', 'success')
            return redirect(url_for('routes.patient_detail', patient_id=patient.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la modification du patient: {e}', 'danger')
    
    return render_template('patient_form.html',
                         form=form,
                         patient=patient,
                         title='Modifier Patient',
                         dashboard_content=True)

# ============================================================================
# COMMENTAIRES MÉDICAUX
# ============================================================================

@routes.route('/analyses/<int:analyse_id>/comment', methods=['POST'])
@login_required
@medecin_required
@audit_action('ADD_COMMENT', 'Analysis')
def add_medical_comment(analyse_id):
    """Ajouter un commentaire médical à une analyse"""
    analyse = AnalyseResult.query.get_or_404(analyse_id)
    
    commentaire = request.form.get('commentaire')
    visible_patient = request.form.get('visible_patient') == 'oui'
    
    if not commentaire:
        flash('Le commentaire ne peut pas être vide', 'danger')
        return redirect(url_for('routes.analyse_detail_page', analyse_id=analyse_id))
    
    try:
        analyse.commentaire_medecin = commentaire
        analyse.commentaire_visible_patient = visible_patient
        analyse.date_modification = utcnow()
        
        db.session.commit()
        
        # Notification au patient si le commentaire est visible
        if visible_patient and analyse.patient.email:
            notification_service.send_email_notification(
                to_email=analyse.patient.email,
                subject="Nouveau commentaire sur votre analyse",
                template="patient_comment_notification",
                analyse=analyse,
                commentaire=commentaire
            )
        
        flash('Commentaire ajouté avec succès!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de l\'ajout du commentaire: {e}', 'danger')
    
    return redirect(url_for('routes.analyse_detail_page', analyse_id=analyse_id))

# ============================================================================
# TÉLÉCHARGEMENTS PDF
# ============================================================================

@routes.route('/analyses/<int:analyse_id>/pdf')
@login_required
@audit_action('DOWNLOAD', 'PDF')
def download_analyse_pdf(analyse_id):
    """Télécharger le PDF d'une analyse"""
    analyse = AnalyseResult.query.get_or_404(analyse_id)
    
    # Vérifier les permissions
    if not current_user.role == RoleEnum.MEDECIN and analyse.user_id != current_user.id:
        flash('Accès non autorisé', 'danger')
        return redirect(url_for('routes.dashboard'))
    
    try:
        pdf_buffer = pdf_service.generate_analysis_pdf(analyse)
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'analyse_{analyse.id}_{analyse.patient.nom}_{analyse.patient.prenom}.pdf'
        )
        
    except Exception as e:
        flash(f'Erreur lors de la génération du PDF: {e}', 'danger')
        return redirect(url_for('routes.analyse_detail_page', analyse_id=analyse_id))

@routes.route('/patients/<int:patient_id>/pdf')
@login_required
@medecin_required
@audit_action('DOWNLOAD', 'PDF')
def download_patient_pdf(patient_id):
    """Télécharger le PDF complet d'un patient"""
    patient = Patient.query.get_or_404(patient_id)
    
    try:
        pdf_buffer = pdf_service.generate_patient_history_pdf(patient)
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'patient_{patient.nom}_{patient.prenom}_historique.pdf'
        )
        
    except Exception as e:
        flash(f'Erreur lors de la génération du PDF: {e}', 'danger')
        return redirect(url_for('routes.patient_detail', patient_id=patient_id))

# ============================================================================
# STATISTIQUES ET TABLEAU DE BORD
# ============================================================================

@routes.route('/statistics')
@login_required
@medecin_required
@audit_action('VIEW', 'Statistics')
def statistics_dashboard():
    """Tableau de bord des statistiques pour les médecins"""
    period = request.args.get('period', '30')
    
    # Convertir en entier et valider
    try:
        period_days = int(period)
    except (ValueError, TypeError):
        period_days = 30
    
    # Date limite selon la période
    date_limit = utcnow() - timedelta(days=period_days)
    
    # Statistiques principales
    stats = {
        'total_patients': Patient.query.count(),
        'total_analyses': AnalyseResult.query.count(),
        'total_anomalies': AnalyseResult.query.filter(
            AnalyseResult.type_anomalie.isnot(None)
        ).count(),
        'precision_rate': 95.2,  # À calculer selon vos métriques
        'new_patients_period': Patient.query.filter(
            Patient.created_at >= date_limit
        ).count(),
        'analyses_period': AnalyseResult.query.filter(
            AnalyseResult.created_at >= date_limit
        ).count(),
        'anomalies_today': AnalyseResult.query.filter(
            and_(
                func.date(AnalyseResult.created_at) == date.today(),
                AnalyseResult.type_anomalie.isnot(None)
            )
        ).count(),
        'pending_reviews': AnalyseResult.query.filter(
            AnalyseResult.commentaire_medecin.is_(None)
        ).count()
    }
    
    # Données pour les graphiques (à implémenter selon vos besoins)
    stats['daily_analyses_data'] = []
    stats['anomaly_types_data'] = {}
    
    # Patients avec anomalies récentes
    stats['top_anomaly_patients'] = []
    
    # Médecins les plus actifs
    stats['top_doctors'] = []
    
    # Analyses récentes
    stats['recent_analyses'] = AnalyseResult.query.order_by(
        desc(AnalyseResult.created_at)
    ).limit(10).all()
    
    return render_template('statistics_dashboard.html',
                         stats=stats,
                         title='Statistiques',
                         dashboard_content=True)

@routes.route('/statistics/export')
@login_required
@medecin_required
@audit_action('EXPORT', 'Statistics')
def export_statistics_csv():
    """Exporter les statistiques en CSV"""
    period = request.args.get('period', '30')
    
    # Convertir en entier et valider
    try:
        period_days = int(period)
    except (ValueError, TypeError):
        period_days = 30
    
    # Récupérer les données statistiques (même logique que statistics_dashboard)
    stats_data = {
        'total_patients': Patient.query.count(),
        'total_analyses': AnalyseResult.query.count(),
        # ... autres statistiques
    }
    
    csv_data = export_service.export_statistics_csv(stats_data)
    return export_service.create_csv_response(csv_data, 'statistiques_diseasedetect')

# ============================================================================
# NOTIFICATIONS
# ============================================================================

@routes.route('/notifications')
@login_required
@audit_action('VIEW', 'Notification')
def view_notifications():
    """Afficher les notifications de l'utilisateur"""
    page = request.args.get('page', 1, type=int)
    
    notifications = Notification.query.filter_by(user_id=current_user.id)\
                                     .order_by(desc(Notification.created_at))\
                                     .paginate(page=page, per_page=20, error_out=False)
    
    unread_count = Notification.query.filter_by(
        user_id=current_user.id, lu=False
    ).count()
    
    return render_template('notifications.html',
                         notifications=notifications,
                         unread_count=unread_count,
                         title='Notifications',
                         dashboard_content=True)

@routes.route('/notifications/<int:notification_id>/mark-read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Marquer une notification comme lue"""
    notification = Notification.query.filter_by(
        id=notification_id, user_id=current_user.id
    ).first_or_404()
    
    notification.lu = True
    notification.date_lecture = utcnow()
    db.session.commit()
    
    return jsonify({'success': True})

@routes.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Marquer toutes les notifications comme lues"""
    Notification.query.filter_by(user_id=current_user.id, lu=False)\
                     .update({'lu': True, 'date_lecture': utcnow()})
    db.session.commit()
    
    return jsonify({'success': True})

@routes.route('/notifications/<int:notification_id>/delete', methods=['DELETE'])
@login_required
def delete_notification(notification_id):
    """Supprimer une notification"""
    notification = Notification.query.filter_by(
        id=notification_id, user_id=current_user.id
    ).first_or_404()
    
    db.session.delete(notification)
    db.session.commit()
    
    return jsonify({'success': True})

@routes.route('/notifications/unread-count')
@login_required
def get_unread_notifications_count():
    """Récupérer le nombre de notifications non lues"""
    count = Notification.query.filter_by(
        user_id=current_user.id, lu=False
    ).count()
    
    return jsonify({'count': count})

# ============================================================================
# ADMINISTRATION (ADMINISTRATEURS SEULEMENT)
# ============================================================================

@routes.route('/admin/users')
@login_required
@admin_required
@audit_action('VIEW', 'User')
def admin_users():
    """Gestion des utilisateurs (admin)"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    role_filter = request.args.get('role', '', type=str)
    status_filter = request.args.get('status', '', type=str)
    
    query = User.query
    
    if search:
        query = query.filter(
            or_(
                User.nom.contains(search),
                User.prenom.contains(search),
                User.email.contains(search),
                User.username.contains(search)
            )
        )
    
    if role_filter:
        query = query.filter(User.role == RoleEnum(role_filter))
    
    if status_filter == 'active':
        query = query.filter(User.is_active == True)
    elif status_filter == 'inactive':
        query = query.filter(User.is_active == False)
    
    users = query.paginate(page=page, per_page=20, error_out=False)
    
    # Statistiques
    stats = {
        'medecins': User.query.filter_by(role=RoleEnum.MEDECIN).count(),
        'patients': User.query.filter_by(role=RoleEnum.PATIENT).count(),
        'admins': User.query.filter_by(role=RoleEnum.ADMINISTRATEUR).count()
    }
    
    return render_template('admin_users.html',
                         users=users,
                         stats=stats,
                         title='Administration - Utilisateurs',
                         dashboard_content=True)

@routes.route('/admin/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
@audit_action('CREATE', 'User')
def admin_create_user():
    """Créer un nouvel utilisateur (admin)"""
    from forms import RegisterForm
    form = RegisterForm()
    
    if form.validate_on_submit():
        try:
            # Vérifier si l'email existe déjà
            if User.query.filter_by(email=form.email.data).first():
                flash('Cet email est déjà utilisé.', 'error')
                return render_template('admin_create_user.html', form=form)
            
            # Hasher le mot de passe
            hashed_password = generate_password_hash(form.password.data)
            
            # Créer l'utilisateur
            user = User(
                nom=form.nom.data,
                prenom=form.prenom.data,
                email=form.email.data,
                password=hashed_password,
                role=RoleEnum(form.role.data),
                is_active=True,
                created_at=datetime.now(timezone.utc),
                last_login=None
            )
            
            db.session.add(user)
            
            # Si c'est un patient, créer le profil patient
            if user.role == RoleEnum.patient:
                patient = Patient(
                    user_id=user.id,
                    numero_dossier=f"PAT{datetime.now().strftime('%Y%m%d')}{user.id}",
                    date_naissance=form.date_naissance.data if hasattr(form, 'date_naissance') else None,
                    telephone=form.telephone.data if hasattr(form, 'telephone') else None,
                    adresse=form.adresse.data if hasattr(form, 'adresse') else None,
                    created_at=datetime.now(timezone.utc)
                )
                db.session.add(patient)
            
            db.session.commit()
            
            flash(f'Utilisateur {user.nom} {user.prenom} créé avec succès!', 'success')
            return redirect(url_for('routes.admin_users'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la création: {str(e)}', 'error')
    
    return render_template('admin_create_user.html', form=form)

@routes.route('/admin/users/<int:user_id>/reset_password', methods=['POST'])
@login_required
@admin_required
@audit_action('RESET', 'Password')
def admin_reset_password(user_id):
    """Réinitialiser le mot de passe d'un utilisateur"""
    user = User.query.get_or_404(user_id)
    
    # Générer un nouveau mot de passe temporaire
    temp_password = generate_temp_password()
    user.password = generate_password_hash(temp_password)
    user.date_modification = utcnow()
    
    db.session.commit()
    
    # Envoyer par email (si service configuré)
    if user.email:
        try:
            notification_service.send_email_notification(
                to_email=user.email,
                subject="Réinitialisation de votre mot de passe",
                template="password_reset_admin",
                user=user,
                temp_password=temp_password
            )
        except Exception as e:
            print(f"Erreur envoi email: {e}")
    
    return jsonify({'success': True})

@routes.route('/admin/audit')
@login_required
@admin_required
@audit_action('VIEW', 'AuditLog')
def admin_audit():
    """Journal d'audit système"""
    page = request.args.get('page', 1, type=int)
    user_search = request.args.get('user_search', '', type=str)
    action_filter = request.args.get('action', '', type=str)
    date_start = request.args.get('date_start', '', type=str)
    date_end = request.args.get('date_end', '', type=str)
    
    query = AuditLog.query
    
    if user_search:
        query = query.join(User).filter(
            or_(
                User.nom.contains(user_search),
                User.prenom.contains(user_search),
                User.email.contains(user_search)
            )
        )
    
    if action_filter:
        query = query.filter(AuditLog.action == action_filter)
    
    if date_start:
        try:
            start_date = datetime.strptime(date_start, '%Y-%m-%d')
            query = query.filter(AuditLog.timestamp >= start_date)
        except ValueError:
            pass
    
    if date_end:
        try:
            end_date = datetime.strptime(date_end, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(AuditLog.timestamp < end_date)
        except ValueError:
            pass
    
    audit_logs = query.order_by(desc(AuditLog.timestamp))\
                      .paginate(page=page, per_page=50, error_out=False)
    
    # Statistiques
    stats = {
        'total_actions': AuditLog.query.count(),
        'today_actions': AuditLog.query.filter(
            func.date(AuditLog.timestamp) == date.today()
        ).count(),
        'critical_actions': AuditLog.query.filter(
            AuditLog.action.in_(['DELETE_PATIENT', 'DELETE_ANALYSIS', 'USER_MANAGEMENT'])
        ).count(),
        'active_users': User.query.filter_by(is_active=True).count()
    }
    
    return render_template('admin_audit.html',
                         audit_logs=audit_logs,
                         stats=stats,
                         title='Administration - Journal d\'Audit',
                         dashboard_content=True)

@routes.route('/admin/audit/export')
@login_required
@admin_required
@audit_action('EXPORT', 'Audit')
def export_audit_csv():
    """Exporter le journal d'audit en CSV"""
    # Appliquer les mêmes filtres que dans admin_audit
    query = AuditLog.query.order_by(desc(AuditLog.timestamp))
    
    # Limiter l'export aux 10000 dernières entrées pour éviter les problèmes de mémoire
    audit_logs = query.limit(10000).all()
    
    csv_data = export_service.export_audit_csv(audit_logs)
    return export_service.create_csv_response(csv_data, 'audit_log_diseasedetect')

# ============================================================================
# RECHERCHE ET ANNOTATION (POUR LA RECHERCHE MÉDICALE)
# ============================================================================

@routes.route('/research')
@login_required
@require_role([RoleEnum.MEDECIN, RoleEnum.ADMINISTRATEUR])
@audit_action('VIEW', 'Research')
def research_data():
    """Interface pour gérer les données de recherche"""
    page = request.args.get('page', 1, type=int)
    anomaly_type = request.args.get('anomaly_type', '', type=str)
    annotation_status = request.args.get('annotation_status', '', type=str)
    period = request.args.get('period', '', type=str)
    
    query = AnalyseResult.query
    
    if anomaly_type:
        if anomaly_type == 'SAINS':
            query = query.filter(AnalyseResult.type_anomalie.is_(None))
        else:
            query = query.filter(AnalyseResult.type_anomalie.contains(anomaly_type))
    
    if annotation_status == 'annotated':
        query = query.filter(AnalyseResult.annotations.any())
    elif annotation_status == 'unannotated':
        query = query.filter(~AnalyseResult.annotations.any())
    
    if period:
        date_limit = datetime.now()
        if period == 'today':
            date_limit -= timedelta(days=1)
        elif period == 'week':
            date_limit -= timedelta(days=7)
        elif period == 'month':
            date_limit -= timedelta(days=30)
        elif period == 'quarter':
            date_limit -= timedelta(days=90)
        
        query = query.filter(AnalyseResult.created_at >= date_limit)
    
    analyses = query.order_by(desc(AnalyseResult.created_at))\
                   .paginate(page=page, per_page=20, error_out=False)
    
    # Statistiques
    stats = {
        'total_analyses': AnalyseResult.query.count(),
        'annotated_analyses': AnalyseResult.query.filter(
            AnalyseResult.annotations.any()
        ).count(),
        'under_review': AnalyseResult.query.join(Annotation).filter(
            Annotation.statut == 'under_review'
        ).count(),
        'validated_analyses': AnalyseResult.query.join(Annotation).filter(
            Annotation.statut == 'validated'
        ).count()
    }
    
    return render_template('research_data.html',
                         analyses=analyses,
                         stats=stats,
                         title='Données de Recherche',
                         dashboard_content=True)

@routes.route('/research/annotate/<int:analyse_id>', methods=['GET', 'POST'])
@login_required
@require_role([RoleEnum.MEDECIN, RoleEnum.ADMINISTRATEUR])
@audit_action('ANNOTATE', 'Analysis')
def annotate_analysis(analyse_id):
    """Interface d'annotation pour la recherche"""
    analyse = AnalyseResult.query.get_or_404(analyse_id)
    form = AnnotationForm()
    
    # Récupérer l'annotation existante pour la recherche
    existing_annotation = Annotation.query.filter_by(
        analyse_id=analyse_id,
        type='RESEARCH' # Utilisation de la nouvelle colonne 'type'
    ).first()
    
    if existing_annotation and request.method == 'GET':
        form.annotation_type.data = existing_annotation.type
        form.annotation.data = existing_annotation.annotation
        form.tags.data = existing_annotation.tags
        form.statut.data = existing_annotation.statut
        form.notes_privees.data = existing_annotation.notes_privees
    
    if form.validate_on_submit():
        try:
            if existing_annotation:
                # Mettre à jour l'annotation existante
                existing_annotation.annotation = form.annotation.data
                existing_annotation.tags = form.tags.data
                existing_annotation.statut = form.statut.data
                existing_annotation.notes_privees = form.notes_privees.data
                existing_annotation.date_modification = utcnow()
                annotation = existing_annotation
            else:
                # Créer une nouvelle annotation
                annotation = Annotation(
                    analyse_id=analyse_id,
                    annotateur_id=current_user.id,
                    type=form.annotation_type.data,
                    annotation=form.annotation.data,
                    tags=form.tags.data,
                    statut=form.statut.data,
                    notes_privees=form.notes_privees.data
                )
                db.session.add(annotation)
            
            db.session.commit()
            
            flash('Annotation enregistrée avec succès!', 'success')
            return redirect(url_for('routes.research_data'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de l\'enregistrement: {e}', 'danger')
    
    return render_template('annotate_analysis.html',
                         analyse=analyse,
                         form=form,
                         title='Annotation pour la Recherche',
                         dashboard_content=True)

@routes.route('/research/export')
@login_required
@require_role([RoleEnum.MEDECIN, RoleEnum.ADMINISTRATEUR])
@audit_action('EXPORT', 'Research')
def export_research_data():
    """Exporter les données de recherche"""
    format_type = request.args.get('format', 'csv', type=str)
    
    # Appliquer les mêmes filtres que dans research_data
    query = AnalyseResult.query
    
    # Limiter à 5000 analyses pour éviter les problèmes de mémoire
    analyses = query.order_by(desc(AnalyseResult.created_at)).limit(5000).all()
    
    if format_type == 'csv':
        csv_data = export_service.export_analyses_csv(analyses)
        return export_service.create_csv_response(csv_data, 'research_data_diseasedetect')
    elif format_type == 'fhir':
        # Exporter la première analyse en FHIR pour exemple
        if analyses:
            fhir_data = export_service.export_to_fhir(analyses[0])
            return export_service.create_json_response(fhir_data, 'analysis_fhir')
    elif format_type == 'hl7':
        # Exporter la première analyse en HL7 pour exemple
        if analyses:
            hl7_data = export_service.export_to_hl7_v2(analyses[0])
            return export_service.create_hl7_response(hl7_data, 'analysis_hl7')
    
    flash('Format d\'export non supporté', 'danger')
    return redirect(url_for('routes.research_data'))