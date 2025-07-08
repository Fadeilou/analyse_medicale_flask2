#!/usr/bin/env python3
"""
Script d'initialisation de la base de données
Créé les tables et ajoute des données de test
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Patient, AnalyseResult, RoleEnum, Notification, AuditLog, Annotation
from werkzeug.security import generate_password_hash
from datetime import datetime, date, timezone
import traceback

def init_database():
    """Initialise la base de données avec les tables et données de base"""
    with app.app_context():
        try:
            print("🔄 Création des tables...")
            db.create_all()
            print("✅ Tables créées avec succès!")
            
            # Vérifier si des utilisateurs existent déjà
            if User.query.first():
                print("ℹ️  Des utilisateurs existent déjà, pas d'initialisation des données de test.")
                return
            
            print("🔄 Création des utilisateurs de base...")
            
            # Créer un administrateur par défaut
            admin = User(
                username='admin',
                email='admin@medicale.com',
                password=generate_password_hash('admin123'),
                role=RoleEnum.ADMINISTRATEUR,
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(admin)
            
            # Créer un médecin par défaut
            medecin = User(
                username='dr_martin',
                email='medecin@medicale.com',
                password=generate_password_hash('medecin123'),
                role=RoleEnum.MEDECIN,
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(medecin)
            
            # Créer quelques patients de test
            patient1 = Patient(
                nom='Dupont',
                prenom='Jean',
                date_naissance=date(1980, 5, 15),
                sexe='M',
                telephone='0123456789',
                email='jean.dupont@email.com',
                adresse='123 Rue de la Santé, 75000 Paris',
                antecedents_medicaux='Hypertension artérielle',
                allergies='Pénicilline',
                medecin_traitant='Dr. Smith',
                created_at=datetime.now(timezone.utc)
            )
            
            patient2 = Patient(
                nom='Martin',
                prenom='Marie',
                date_naissance=date(1990, 8, 22),
                sexe='F',
                telephone='0987654321',
                email='marie.martin@email.com',
                adresse='456 Avenue de la Paix, 69000 Lyon',
                antecedents_medicaux='Diabète type 2',
                allergies='Aucune',
                medecin_traitant='Dr. Johnson',
                created_at=datetime.now(timezone.utc)
            )
            
            db.session.add(patient1)
            db.session.add(patient2)
            
            # Créer un utilisateur patient lié à patient1
            user_patient = User(
                username='jean_dupont',
                email='jean.dupont@email.com',
                password=generate_password_hash('patient123'),
                role=RoleEnum.PATIENT,
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(user_patient)
            
            # Commitons les utilisateurs et patients d'abord
            db.session.commit()
            
            # Lier le patient1 au user_patient
            user_patient.patient_id = patient1.id
            db.session.commit()
            
            print("✅ Utilisateurs et patients créés avec succès!")
            print("\n📋 Comptes créés:")
            print("👤 Admin: admin / admin123")
            print("🩺 Médecin: dr_martin / medecin123")
            print("🧑‍⚕️ Patient: jean_dupont / patient123")
            
            # Créer une notification de bienvenue pour l'admin
            notification = Notification(
                user_id=admin.id,
                titre='Bienvenue sur la plateforme d\'analyse médicale',
                message='Votre système d\'analyse médicale est maintenant opérationnel. Vous pouvez commencer à gérer les utilisateurs et superviser les analyses.',
                type_notification='SYSTEME',
                lu=False,
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(notification)
            
            db.session.commit()
            print("✅ Base de données initialisée avec succès!")
            
        except Exception as e:
            print(f"❌ Erreur lors de l'initialisation: {e}")
            print(traceback.format_exc())
            db.session.rollback()

def reset_database():
    """ATTENTION: Supprime toutes les données!"""
    with app.app_context():
        try:
            response = input("⚠️  ATTENTION: Cela va supprimer TOUTES les données! Tapez 'OUI' pour confirmer: ")
            if response != 'OUI':
                print("❌ Opération annulée.")
                return
                
            print("🔄 Suppression des tables...")
            db.drop_all()
            print("✅ Tables supprimées!")
            
            print("🔄 Recréation des tables...")
            init_database()
            
        except Exception as e:
            print(f"❌ Erreur lors de la réinitialisation: {e}")
            print(traceback.format_exc())

def show_users():
    """Affiche tous les utilisateurs"""
    with app.app_context():
        try:
            users = User.query.all()
            print(f"\n👥 {len(users)} utilisateur(s) trouvé(s):")
            for user in users:
                patient_info = f" (Patient: {user.patient_profile.nom} {user.patient_profile.prenom})" if user.patient_profile else ""
                print(f"  - {user.username} ({user.email}) - {user.role.value}{patient_info}")
                
            patients = Patient.query.all()
            print(f"\n🏥 {len(patients)} patient(s) trouvé(s):")
            for patient in patients:
                user_info = f" (Compte: {patient.user_account.username})" if patient.user_account else " (Pas de compte utilisateur)"
                print(f"  - {patient.nom} {patient.prenom} ({patient.email}){user_info}")
                
        except Exception as e:
            print(f"❌ Erreur: {e}")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == 'reset':
            reset_database()
        elif sys.argv[1] == 'users':
            show_users()
        else:
            print("Usage: python init_db.py [reset|users]")
    else:
        init_database()
