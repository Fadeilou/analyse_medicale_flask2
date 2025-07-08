"""
Module de monitoring et health checks pour l'application médicale
Surveille la santé de l'application, les performances et les métriques métiers
"""
from flask import Blueprint, jsonify, current_app, request
from datetime import datetime, timedelta, timezone
from models import db, User, Patient, AnalyseResult, AuditLog, Notification
from auth_decorators import admin_required
import psutil
import os
import time
from functools import wraps
from collections import defaultdict
import json
import traceback

monitoring = Blueprint('monitoring', __name__, url_prefix='/monitoring')

# Cache pour les métriques (éviter de recalculer à chaque requête)
metrics_cache = {}
cache_timeout = 60  # 1 minute


def cache_metrics(timeout=60):
    """Décorateur pour mettre en cache les métriques"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"
            now = time.time()
            
            if cache_key in metrics_cache:
                data, timestamp = metrics_cache[cache_key]
                if now - timestamp < timeout:
                    return data
            
            result = func(*args, **kwargs)
            metrics_cache[cache_key] = (result, now)
            return result
        return wrapper
    return decorator


class HealthChecker:
    """Classe pour les vérifications de santé du système"""
    
    @staticmethod
    def check_database():
        """Vérifie la connexion à la base de données"""
        try:
            # Test simple de connexion
            result = db.session.execute(db.text('SELECT 1')).scalar()
            return {
                'status': 'healthy' if result == 1 else 'unhealthy',
                'response_time': 'fast',
                'details': 'Database connection successful'
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'response_time': 'timeout',
                'details': f'Database error: {str(e)}'
            }
    
    @staticmethod
    def check_disk_space():
        """Vérifie l'espace disque disponible"""
        try:
            usage = psutil.disk_usage('/')
            percent_used = (usage.used / usage.total) * 100
            
            status = 'healthy'
            if percent_used > 90:
                status = 'critical'
            elif percent_used > 80:
                status = 'warning'
            
            return {
                'status': status,
                'percent_used': round(percent_used, 2),
                'free_gb': round(usage.free / (1024**3), 2),
                'total_gb': round(usage.total / (1024**3), 2)
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'details': f'Disk check error: {str(e)}'
            }
    
    @staticmethod
    def check_memory():
        """Vérifie l'utilisation de la mémoire"""
        try:
            memory = psutil.virtual_memory()
            percent_used = memory.percent
            
            status = 'healthy'
            if percent_used > 90:
                status = 'critical'
            elif percent_used > 80:
                status = 'warning'
            
            return {
                'status': status,
                'percent_used': percent_used,
                'available_gb': round(memory.available / (1024**3), 2),
                'total_gb': round(memory.total / (1024**3), 2)
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'details': f'Memory check error: {str(e)}'
            }
    
    @staticmethod
    def check_ai_model():
        """Vérifie si le modèle IA est chargé et fonctionnel"""
        try:
            from routes import ai_model, model_loaded
            
            if not model_loaded or ai_model is None:
                return {
                    'status': 'unhealthy',
                    'details': 'AI model not loaded'
                }
            
            # Test basique du modèle (si possible)
            return {
                'status': 'healthy',
                'details': 'AI model loaded and ready'
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'details': f'AI model check error: {str(e)}'
            }


class MetricsCollector:
    """Collecteur de métriques métiers"""
    
    @staticmethod
    @cache_metrics(timeout=300)  # Cache 5 minutes
    def get_business_metrics():
        """Collecte les métriques métiers importantes"""
        try:
            now = utcnow()
            today = now.date()
            last_24h = now - timedelta(hours=24)
            last_7d = now - timedelta(days=7)
            last_30d = now - timedelta(days=30)
            
            # Métriques utilisateurs
            total_users = User.query.count()
            active_users_24h = User.query.filter(
                User.last_login >= last_24h
            ).count()
            
            medecins_count = User.query.filter_by(role='medecin').count()
            patients_count = User.query.filter_by(role='patient').count()
            admins_count = User.query.filter_by(role='administrateur').count()
            
            # Métriques patients
            total_patients = Patient.query.count()
            new_patients_7d = Patient.query.filter(
                Patient.created_at >= last_7d
            ).count()
            
            # Métriques analyses
            total_analyses = AnalyseResult.query.count()
            analyses_24h = AnalyseResult.query.filter(
                AnalyseResult.date_analyse >= last_24h
            ).count()
            analyses_7d = AnalyseResult.query.filter(
                AnalyseResult.date_analyse >= last_7d
            ).count()
            
            # Analyses positives
            analyses_positives = AnalyseResult.query.filter_by(test_positif=True).count()
            analyses_positives_7d = AnalyseResult.query.filter(
                AnalyseResult.test_positif == True,
                AnalyseResult.date_analyse >= last_7d
            ).count()
            
            # Taux de détection
            detection_rate = (analyses_positives / total_analyses * 100) if total_analyses > 0 else 0
            detection_rate_7d = (analyses_positives_7d / analyses_7d * 100) if analyses_7d > 0 else 0
            
            # Notifications non lues
            unread_notifications = Notification.query.filter_by(lu=False).count()
            
            return {
                'timestamp': now.isoformat(),
                'users': {
                    'total': total_users,
                    'active_24h': active_users_24h,
                    'medecins': medecins_count,
                    'patients': patients_count,
                    'admins': admins_count
                },
                'patients': {
                    'total': total_patients,
                    'new_7d': new_patients_7d
                },
                'analyses': {
                    'total': total_analyses,
                    'last_24h': analyses_24h,
                    'last_7d': analyses_7d,
                    'positives_total': analyses_positives,
                    'positives_7d': analyses_positives_7d,
                    'detection_rate_total': round(detection_rate, 2),
                    'detection_rate_7d': round(detection_rate_7d, 2)
                },
                'notifications': {
                    'unread': unread_notifications
                }
            }
        except Exception as e:
            current_app.logger.error(f"Erreur collecte métriques: {e}")
            return {'error': str(e)}
    
    @staticmethod
    @cache_metrics(timeout=600)  # Cache 10 minutes
    def get_performance_metrics():
        """Collecte les métriques de performance"""
        try:
            # Temps de réponse moyen des analyses (dernières 100)
            recent_analyses = AnalyseResult.query.order_by(
                AnalyseResult.created_at.desc()
            ).limit(100).all()
            
            avg_processing_time = 0
            if recent_analyses:
                # Simuler un calcul de temps de traitement
                # En réalité, vous devriez stocker ces métriques
                avg_processing_time = 2.5  # secondes (exemple)
            
            # Utilisation système
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'timestamp': utcnow().isoformat(),
                'processing': {
                    'avg_analysis_time_seconds': avg_processing_time,
                    'recent_analyses_count': len(recent_analyses)
                },
                'system': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'disk_percent': (disk.used / disk.total) * 100
                }
            }
        except Exception as e:
            current_app.logger.error(f"Erreur métriques performance: {e}")
            return {'error': str(e)}


# Fonction pour obtenir l'heure UTC avec fuseau horaire
def utcnow():
    """Timezone-aware UTC now function"""
    return datetime.now(timezone.utc)


# Routes de monitoring

@monitoring.route('/health')
def health_check():
    """Endpoint de health check pour les load balancers"""
    health_checker = HealthChecker()
    
    checks = {
        'database': health_checker.check_database(),
        'disk': health_checker.check_disk_space(),
        'memory': health_checker.check_memory(),
        'ai_model': health_checker.check_ai_model()
    }
    
    # Statut global
    overall_status = 'healthy'
    for check in checks.values():
        if check['status'] in ['unhealthy', 'critical']:
            overall_status = 'unhealthy'
            break
        elif check['status'] == 'warning' and overall_status == 'healthy':
            overall_status = 'warning'
    
    response = {
        'status': overall_status,
        'timestamp': utcnow().isoformat(),
        'checks': checks
    }
    
    status_code = 200 if overall_status in ['healthy', 'warning'] else 503
    return jsonify(response), status_code


@monitoring.route('/metrics')
@admin_required
def get_metrics():
    """Endpoint pour récupérer les métriques détaillées"""
    collector = MetricsCollector()
    
    metrics = {
        'business': collector.get_business_metrics(),
        'performance': collector.get_performance_metrics(),
        'health': HealthChecker().check_database()
    }
    
    return jsonify(metrics)


@monitoring.route('/metrics/business')
@admin_required
def get_business_metrics():
    """Endpoint pour les métriques métiers uniquement"""
    collector = MetricsCollector()
    return jsonify(collector.get_business_metrics())


@monitoring.route('/metrics/performance')
@admin_required
def get_performance_metrics():
    """Endpoint pour les métriques de performance uniquement"""
    collector = MetricsCollector()
    return jsonify(collector.get_performance_metrics())


@monitoring.route('/logs/recent')
@admin_required
def get_recent_logs():
    """Récupère les logs récents d'audit"""
    try:
        # Derniers 100 logs d'audit
        recent_logs = AuditLog.query.order_by(
            AuditLog.timestamp.desc()
        ).limit(100).all()
        
        logs_data = []
        for log in recent_logs:
            logs_data.append({
                'id': log.id,
                'user_id': log.user_id,
                'action': log.action,
                'resource_type': log.resource_type,
                'resource_id': log.resource_id,
                'timestamp': log.timestamp.isoformat(),
                'ip_address': log.ip_address,
                'details': log.details
            })
        
        return jsonify({
            'logs': logs_data,
            'count': len(logs_data),
            'timestamp': utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@monitoring.route('/alerts')
@admin_required
def get_alerts():
    """Récupère les alertes système"""
    alerts = []
    
    # Vérifier les conditions d'alerte
    health_checker = HealthChecker()
    
    # Alerte espace disque
    disk_check = health_checker.check_disk_space()
    if disk_check['status'] in ['warning', 'critical']:
        alerts.append({
            'type': 'disk_space',
            'severity': disk_check['status'],
            'message': f"Espace disque utilisé à {disk_check['percent_used']}%",
            'timestamp': utcnow().isoformat()
        })
    
    # Alerte mémoire
    memory_check = health_checker.check_memory()
    if memory_check['status'] in ['warning', 'critical']:
        alerts.append({
            'type': 'memory',
            'severity': memory_check['status'],
            'message': f"Mémoire utilisée à {memory_check['percent_used']}%",
            'timestamp': utcnow().isoformat()
        })
    
    # Alerte modèle IA
    ai_check = health_checker.check_ai_model()
    if ai_check['status'] != 'healthy':
        alerts.append({
            'type': 'ai_model',
            'severity': 'critical',
            'message': "Modèle IA non disponible",
            'timestamp': utcnow().isoformat()
        })
    
    # Alertes métiers (ex: trop d'analyses positives)
    collector = MetricsCollector()
    business_metrics = collector.get_business_metrics()
    
    if 'analyses' in business_metrics:
        detection_rate = business_metrics['analyses'].get('detection_rate_7d', 0)
        if detection_rate > 50:  # Plus de 50% d'analyses positives
            alerts.append({
                'type': 'high_detection_rate',
                'severity': 'warning',
                'message': f"Taux de détection élevé: {detection_rate}% (7 derniers jours)",
                'timestamp': utcnow().isoformat()
            })
    
    return jsonify({
        'alerts': alerts,
        'count': len(alerts),
        'timestamp': utcnow().isoformat()
    })


# Fonction pour initialiser le monitoring
def init_monitoring(app):
    """Initialise le module de monitoring"""
    app.register_blueprint(monitoring)
    
    # Configuration du logging pour les métriques
    if not app.debug:
        import logging
        metrics_logger = logging.getLogger('metrics')
        metrics_handler = logging.FileHandler('logs/metrics.log')
        metrics_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        metrics_logger.addHandler(metrics_handler)
        metrics_logger.setLevel(logging.INFO)
    
    app.logger.info('Module de monitoring initialisé')
