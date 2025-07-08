"""
Migration pour ajouter les fonctionnalités de sécurité avancée
Ajoute les champs 2FA, chiffrement et audit trail renforcé
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers
revision = '002_add_security_features'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade():
    """Ajoute les nouvelles fonctionnalités de sécurité"""
    
    # Ajouter les champs 2FA à la table User
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('two_factor_enabled', sa.Boolean(), default=False))
        batch_op.add_column(sa.Column('two_factor_secret', sa.String(32), nullable=True))
        batch_op.add_column(sa.Column('backup_codes', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('last_2fa_use', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('failed_login_attempts', sa.Integer(), default=0))
        batch_op.add_column(sa.Column('account_locked_until', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('password_reset_token', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('password_reset_expires', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('email_verified', sa.Boolean(), default=False))
        batch_op.add_column(sa.Column('email_verification_token', sa.String(100), nullable=True))
    
    # Ajouter des champs de sécurité à la table Patient
    with op.batch_alter_table('patient', schema=None) as batch_op:
        batch_op.add_column(sa.Column('data_encrypted', sa.Boolean(), default=False))
        batch_op.add_column(sa.Column('consent_given', sa.Boolean(), default=False))
        batch_op.add_column(sa.Column('consent_date', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('data_retention_until', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('anonymized', sa.Boolean(), default=False))
        batch_op.add_column(sa.Column('anonymized_date', sa.DateTime(), nullable=True))
    
    # Ajouter des champs de sécurité à la table AnalyseResult
    with op.batch_alter_table('analyse_result', schema=None) as batch_op:
        batch_op.add_column(sa.Column('data_encrypted', sa.Boolean(), default=False))
        batch_op.add_column(sa.Column('checksum', sa.String(64), nullable=True))
        batch_op.add_column(sa.Column('signed_by', sa.Integer(), sa.ForeignKey('user.id'), nullable=True))
        batch_op.add_column(sa.Column('signature_date', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('access_restricted', sa.Boolean(), default=False))
    
    # Ajouter des index pour les performances
    op.create_index('idx_user_email_verified', 'user', ['email_verified'])
    op.create_index('idx_user_account_locked', 'user', ['account_locked_until'])
    op.create_index('idx_patient_anonymized', 'patient', ['anonymized'])
    op.create_index('idx_analyse_encrypted', 'analyse_result', ['data_encrypted'])
    
    # Créer une table pour les sessions sécurisées
    op.create_table('secure_session',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('session_id', sa.String(128), unique=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('last_activity', sa.DateTime(), default=datetime.utcnow),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('security_flags', sa.JSON(), nullable=True)
    )
    
    # Créer une table pour les logs de sécurité
    op.create_table('security_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),  # LOW, MEDIUM, HIGH, CRITICAL
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(255), nullable=True),
        sa.Column('additional_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('resolved', sa.Boolean(), default=False),
        sa.Column('resolved_by', sa.Integer(), sa.ForeignKey('user.id'), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True)
    )
    
    # Créer une table pour les tokens API (si besoin)
    op.create_table('api_token',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('token_hash', sa.String(128), unique=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('permissions', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('last_used', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True)
    )
    
    # Index pour les nouvelles tables
    op.create_index('idx_secure_session_user', 'secure_session', ['user_id'])
    op.create_index('idx_secure_session_expires', 'secure_session', ['expires_at'])
    op.create_index('idx_security_log_event', 'security_log', ['event_type'])
    op.create_index('idx_security_log_severity', 'security_log', ['severity'])
    op.create_index('idx_security_log_created', 'security_log', ['created_at'])
    op.create_index('idx_api_token_user', 'api_token', ['user_id'])
    op.create_index('idx_api_token_active', 'api_token', ['is_active'])


def downgrade():
    """Supprime les fonctionnalités de sécurité ajoutées"""
    
    # Supprimer les nouvelles tables
    op.drop_table('api_token')
    op.drop_table('security_log')
    op.drop_table('secure_session')
    
    # Supprimer les index
    op.drop_index('idx_analyse_encrypted')
    op.drop_index('idx_patient_anonymized')
    op.drop_index('idx_user_account_locked')
    op.drop_index('idx_user_email_verified')
    
    # Supprimer les colonnes ajoutées
    with op.batch_alter_table('analyse_result', schema=None) as batch_op:
        batch_op.drop_column('access_restricted')
        batch_op.drop_column('signature_date')
        batch_op.drop_column('signed_by')
        batch_op.drop_column('checksum')
        batch_op.drop_column('data_encrypted')
    
    with op.batch_alter_table('patient', schema=None) as batch_op:
        batch_op.drop_column('anonymized_date')
        batch_op.drop_column('anonymized')
        batch_op.drop_column('data_retention_until')
        batch_op.drop_column('consent_date')
        batch_op.drop_column('consent_given')
        batch_op.drop_column('data_encrypted')
    
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('email_verification_token')
        batch_op.drop_column('email_verified')
        batch_op.drop_column('password_reset_expires')
        batch_op.drop_column('password_reset_token')
        batch_op.drop_column('account_locked_until')
        batch_op.drop_column('failed_login_attempts')
        batch_op.drop_column('last_2fa_use')
        batch_op.drop_column('backup_codes')
        batch_op.drop_column('two_factor_secret')
        batch_op.drop_column('two_factor_enabled')


if __name__ == '__main__':
    """Script autonome pour appliquer la migration"""
    print("🔄 Application de la migration de sécurité...")
    
    # Note: En production, utiliser Alembic pour les migrations
    # alembic upgrade head
    
    # Pour un test rapide sans Alembic:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from app import app, db
    
    with app.app_context():
        try:
            # Simulation de la migration (à adapter selon vos besoins)
            print("⚠️  Note: Cette migration nécessite Alembic en production")
            print("✅ Migration préparée. Utilisez: alembic upgrade head")
        except Exception as e:
            print(f"❌ Erreur: {e}")
