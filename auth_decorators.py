from functools import wraps
from flask import abort, request, session, current_app
from flask_login import current_user
from models import AuditLog, db, RoleEnum
from datetime import datetime
import json

def require_role(role):
    """Décorateur pour vérifier le rôle de l'utilisateur"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            if isinstance(role, list):
                if current_user.role not in role:
                    abort(403)
            else:
                if current_user.role != role:
                    abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def medecin_required(f):
    """Décorateur pour restreindre l'accès aux médecins uniquement"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_medecin():
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Décorateur pour restreindre l'accès aux administrateurs uniquement"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def log_user_activity(action, resource_type, resource_id=None, details=None):
    """Fonction pour enregistrer les activités des utilisateurs"""
    try:
        if current_user.is_authenticated:
            audit_log = AuditLog(
                user_id=current_user.id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details if isinstance(details, dict) else None,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            db.session.add(audit_log)
            db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Erreur lors de l'enregistrement de l'audit: {e}")

def audit_action(action, resource_type):
    """Décorateur pour enregistrer automatiquement les actions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Exécuter la fonction
            result = f(*args, **kwargs)
            
            # Enregistrer l'action
            resource_id = kwargs.get('id') or kwargs.get('patient_id') or kwargs.get('analyse_id')
            log_user_activity(action, resource_type, resource_id)
            
            return result
        return decorated_function
    return decorator
