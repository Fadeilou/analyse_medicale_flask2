#!/usr/bin/env python3
"""
Migration pour corriger la longueur du champ password
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from sqlalchemy import text
import traceback

def migrate_password_field():
    """Mise à jour de la longueur du champ password"""
    with app.app_context():
        try:
            print("🔄 Migration du champ password...")
            
            # Exécuter la migration SQL directement
            db.session.execute(text("ALTER TABLE \"user\" ALTER COLUMN password TYPE VARCHAR(255);"))
            db.session.commit()
            
            print("✅ Migration du champ password terminée avec succès!")
            
        except Exception as e:
            print(f"❌ Erreur lors de la migration: {e}")
            print(traceback.format_exc())
            db.session.rollback()

if __name__ == '__main__':
    migrate_password_field()
