"""
Database Reset and Migration Script

This script performs a complete reset of the database and runs all migrations.
It follows these steps:
1. Drops the entire public schema to clean all tables and types
2. Recreates the public schema
3. Runs the combined migration that sets up all tables
"""

import os
from server.config.database import db
from server.app import create_app
from flask_migrate import Migrate
from sqlalchemy import text

def reset_database(app):
    """
    Completely resets the database by dropping and recreating the public schema.
    This removes all tables, types, and other database objects.
    """
    print("Step 1: Resetting database...")
    with app.app_context():
        with db.engine.connect() as conn:
            # Drop any remaining custom types first
            conn.execute(text('DROP TYPE IF EXISTS event_source CASCADE'))
            conn.execute(text('DROP TYPE IF EXISTS event_type CASCADE'))
            # Drop everything in the database
            conn.execute(text('DROP SCHEMA public CASCADE'))
            # Recreate empty schema
            conn.execute(text('CREATE SCHEMA public'))
            conn.commit()
    print("Database reset complete!")

def run_migrations(app):
    """
    Runs all migrations to recreate the database structure.
    Uses the combined migration that creates all tables in the correct order.
    """
    print("\nStep 2: Running migrations...")
    os.environ['FLASK_APP'] = 'server/migrations.py'
    os.system('flask db upgrade')
    print("Migrations complete!")

def main():
    """
    Main function that orchestrates the database reset and migration process.
    """
    print("Starting database reset and migration process...")
    
    # Create Flask application instance
    app = create_app()
    
    # Initialize Flask-Migrate
    migrate = Migrate(app, db)
    
    try:
        # Step 1: Reset the database
        reset_database(app)
        
        # Step 2: Run migrations
        run_migrations(app)
        
        print("\nSuccess! Database has been reset and all tables have been recreated.")
        
    except Exception as e:
        print(f"\nError occurred during database reset and migration:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        raise

if __name__ == '__main__':
    main() 