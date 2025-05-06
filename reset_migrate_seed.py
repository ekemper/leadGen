"""
Database Reset and Migration Script

This script performs a complete reset of the database and runs all migrations.
It follows these steps:
1. Drops the entire public schema to clean all tables and types
2. Recreates the public schema
3. Runs the combined migration that sets up all tables
4. Seeds the database with initial data
"""

import os
from server.config.database import db
from server.app import create_app
from flask_migrate import Migrate
from sqlalchemy import text, inspect
from server.models import Organization, Campaign, User
from server.models.campaign import CampaignStatus
from datetime import datetime
import uuid
import bcrypt

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
    """Run database migrations"""
    print("\nStep 2: Running migrations...")
    try:
        with app.app_context():
            # Run migrations
            with app.app_context():
                db.create_all()
                db.session.commit()
            
            # Debug: Check database schema
            print("\nDebug: Checking database schema...")
            inspector = inspect(db.engine)
            for table_name in inspector.get_table_names():
                print(f"\nTable: {table_name}")
                for column in inspector.get_columns(table_name):
                    print(f"  Column: {column['name']}, Type: {column['type']}")
            
            print("\nMigrations complete!")
    except Exception as e:
        print(f"\nError during migrations: {str(e)}")
        raise

def seed_database(app):
    """
    Seeds the database with initial data.
    This includes:
    1. A default organization
    2. A test user
    3. Sample campaigns with proper status fields
    """
    print("\nStep 3: Seeding database...")
    with app.app_context():
        try:
            # Create test user with hashed password
            password = "password123"
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            test_user = User(
                email="test@example.com",
                password=hashed,
                failed_attempts=0
            )
            db.session.add(test_user)
            db.session.flush()  # Flush to get the user ID

            # Create default organization
            default_org = Organization(
                name="Default Organization",
                description="This is the default organization created during database seeding."
            )
            db.session.add(default_org)
            db.session.flush()  # Flush to get the organization ID

            # Create sample campaigns with proper status fields
            sample_campaigns = [
                Campaign(
                    name="Sample SEO Campaign",
                    description="A sample campaign targeting SEO professionals",
                    organization_id=default_org.id,
                    status=CampaignStatus.CREATED,
                    status_message="Campaign created and ready to start",
                    job_status={},
                    job_ids={}
                ),
                Campaign(
                    name="Sample Marketing Campaign",
                    description="A sample campaign targeting marketing professionals",
                    organization_id=default_org.id,
                    status=CampaignStatus.COMPLETED,
                    status_message="Campaign completed successfully",
                    job_status={
                        "fetch_leads": {"status": "completed", "timestamp": datetime.utcnow().isoformat()},
                        "enrich_leads": {"status": "completed", "timestamp": datetime.utcnow().isoformat()},
                        "email_verification": {"status": "completed", "timestamp": datetime.utcnow().isoformat()},
                        "generate_emails": {"status": "completed", "timestamp": datetime.utcnow().isoformat()}
                    },
                    job_ids={
                        "fetch_leads": str(uuid.uuid4()),
                        "enrich_leads": str(uuid.uuid4()),
                        "email_verification": str(uuid.uuid4()),
                        "generate_emails": str(uuid.uuid4())
                    }
                )
            ]

            for campaign in sample_campaigns:
                db.session.add(campaign)

            # Commit all changes
            db.session.commit()
            print("Database seeding complete!")

        except Exception as e:
            db.session.rollback()
            print(f"Error during database seeding: {str(e)}")
            raise

def main():
    """
    Main function that orchestrates the database reset, migration, and seeding process.
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
        
        # Step 3: Seed the database
        seed_database(app)
        
        print("\nSuccess! Database has been reset, migrated, and seeded with initial data.")
        
    except Exception as e:
        print(f"\nError occurred during database reset and migration:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        raise

if __name__ == '__main__':
    main() 