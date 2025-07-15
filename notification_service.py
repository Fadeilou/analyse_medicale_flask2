from flask import current_app
from flask_mail import Mail, Message
from models import db, Notification, User, AnalyseResult, RoleEnum
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class NotificationService:
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        # Configuration email (à adapter selon vos besoins)
        app.config.setdefault('MAIL_SERVER', 'smtp.gmail.com')
        app.config.setdefault('MAIL_PORT', 587)
        app.config.setdefault('MAIL_USE_TLS', True)
        app.config.setdefault('MAIL_USERNAME', 'your-email@gmail.com')
        app.config.setdefault('MAIL_PASSWORD', 'your-app-password')
        
        self.mail = Mail(app)
    
    def create_notification(self, user_id, titre, message, type_notification, analyse_id=None):
        """Créer une notification en base de données"""
        try:
            notification = Notification(
                user_id=user_id,
                titre=titre,
                message=message,
                type_notification=type_notification,
                analyse_id=analyse_id
            )
            db.session.add(notification)
            db.session.commit()
            return notification
        except Exception as e:
            current_app.logger.error(f"Erreur création notification: {e}")
            db.session.rollback()
            return None
    
    def notify_anomalie_grave(self, analyse_result):
        """Notifier en cas d'anomalie grave détectée"""
        if not analyse_result.test_positif:
            return
        
        # Vérifier si c'est une anomalie grave
        anomalies_graves = ['DREPANOCYTES', 'SCHIZOCYTES']
        if not any(anomalie in analyse_result.type_anomalie for anomalie in anomalies_graves):
            return
        
        # Notifier le médecin qui a fait l'analyse
        titre = "⚠️ Anomalie grave détectée"
        message = f"Une anomalie grave a été détectée dans l'analyse du patient {analyse_result.patient.nom} {analyse_result.patient.prenom}. Vérification recommandée."
        
        self.create_notification(
            user_id=analyse_result.user_id,
            titre=titre,
            message=message,
            type_notification="ANOMALIE_GRAVE",
            analyse_id=analyse_result.id
        )
        
        # Envoyer email si configuré
        self.send_email_notification(analyse_result.medecin.email, titre, message)
    
    def notify_results_available(self, analyse_result):
        """Notifier le patient que ses résultats sont disponibles"""
        patient = analyse_result.patient
        
        # Créer notification pour le compte patient s'il existe
        if patient.user_account:
            titre = "📋 Nouveaux résultats d'analyse disponibles"
            message = f"Vos résultats d'analyse du {analyse_result.date_analyse.strftime('%d/%m/%Y')} sont maintenant disponibles."
            
            self.create_notification(
                user_id=patient.user_account.id,
                titre=titre,
                message=message,
                type_notification="ANALYSE_DISPONIBLE",
                analyse_id=analyse_result.id
            )
        
        # Envoyer email si le patient a fourni son email
        if patient.email:
            titre = "Résultats d'analyse DiseaseDetect disponibles"
            message = f"""Bonjour {patient.prenom} {patient.nom},

Vos résultats d'analyse du {analyse_result.date_analyse.strftime('%d/%m/%Y')} sont maintenant disponibles sur votre espace patient DiseaseDetect.

Connectez-vous à votre compte pour consulter vos résultats.

Cordialement,
L'équipe DiseaseDetect"""
            
            self.send_email_notification(patient.email, titre, message)
    
    def send_email_notification(self, to_email, subject, body):
        """Envoyer une notification par email"""
        try:
            if not current_app.config.get('MAIL_USERNAME'):
                current_app.logger.warning("Configuration email non définie")
                return False
            
            msg = Message(
                subject=subject,
                sender=current_app.config['MAIL_USERNAME'],
                recipients=[to_email],
                body=body
            )
            
            self.mail.send(msg)
            current_app.logger.info(f"Email envoyé à {to_email}")
            return True
            
        except Exception as e:
            current_app.logger.error(f"Erreur envoi email: {e}")
            return False
    
    def get_user_notifications(self, user_id, unread_only=False):
        """Récupérer les notifications d'un utilisateur"""
        query = Notification.query.filter_by(user_id=user_id)
        if unread_only:
            query = query.filter_by(lu=False)
        return query.order_by(Notification.created_at.desc()).all()
    
    def mark_as_read(self, notification_id, user_id):
        """Marquer une notification comme lue"""
        notification = Notification.query.filter_by(
            id=notification_id, 
            user_id=user_id
        ).first()
        
        if notification:
            notification.lu = True
            db.session.commit()
            return True
        return False

# Instance globale
notification_service = NotificationService()
