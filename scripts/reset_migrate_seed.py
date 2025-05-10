"""
DEPRECATED: Use scripts/full_db_reset.py for all reset, migration, and seeding operations.
This script is retained for backward compatibility and for importable seeding logic only.

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
from server.models import Organization, Campaign, User, Lead, Event
from server.models.campaign import CampaignStatus
from server.models.job import Job
from datetime import datetime, timedelta
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
    Seeds the database with initial data for all tables, ensuring meaningful relationships.
    - 1 default organization
    - 2 users
    - 2 campaigns (each linked to org)
    - 2 jobs per campaign
    - 3 leads per campaign
    - 2 events (linked to campaigns, users)
    """
    print("\nStep 3: Seeding database...")
    with app.app_context():
        try:
            # --- Users ---
            password = "password123"
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            user1 = User(email="test@example.com", password=hashed, failed_attempts=0)
            user2 = User(email="admin@example.com", password=hashed, failed_attempts=0)
            db.session.add_all([user1, user2])
            db.session.flush()

            # --- Organization ---
            default_org = Organization(
                name="Default Organization",
                description="This is the default organization created during database seeding."
            )
            db.session.add(default_org)
            db.session.flush()

            # --- Campaigns ---
            campaign1 = Campaign(
                name="Sample SEO Campaign",
                description="A sample campaign targeting SEO professionals",
                organization_id=default_org.id,
                status=CampaignStatus.CREATED,
                status_message="Campaign created and ready to start",
                searchUrl="https://app.apollo.io/#/people?page=1&personLocations%5B%5D=United%20States",
                count=10,
                excludeGuessedEmails=True,
                excludeNoEmails=True,
                getEmails=True
            )
            campaign2 = Campaign(
                name="Sample Marketing Campaign",
                description="A sample campaign targeting marketing professionals",
                organization_id=default_org.id,
                status=CampaignStatus.COMPLETED,
                status_message="Campaign completed successfully",
                searchUrl="https://app.apollo.io/#/people?page=1&personLocations%5B%5D=United%20States",
                count=20,
                excludeGuessedEmails=False,
                excludeNoEmails=False,
                getEmails=True
            )
            db.session.add_all([campaign1, campaign2])
            db.session.flush()

            # --- Jobs ---
            now = datetime.utcnow()
            jobs = [
                Job(
                    id=str(uuid.uuid4()),
                    campaign_id=campaign1.id,
                    job_type="fetch_leads",
                    status="completed",
                    result={"leads_fetched": 100},
                    started_at=now - timedelta(minutes=10),
                    completed_at=now - timedelta(minutes=9)
                ),
                Job(
                    id=str(uuid.uuid4()),
                    campaign_id=campaign1.id,
                    job_type="enrich_leads",
                    status="completed",
                    result={"enriched": 100},
                    started_at=now - timedelta(minutes=8),
                    completed_at=now - timedelta(minutes=7)
                ),
                Job(
                    id=str(uuid.uuid4()),
                    campaign_id=campaign2.id,
                    job_type="fetch_leads",
                    status="completed",
                    result={"leads_fetched": 200},
                    started_at=now - timedelta(minutes=20),
                    completed_at=now - timedelta(minutes=19)
                ),
                Job(
                    id=str(uuid.uuid4()),
                    campaign_id=campaign2.id,
                    job_type="enrich_leads",
                    status="completed",
                    result={"enriched": 200},
                    started_at=now - timedelta(minutes=18),
                    completed_at=now - timedelta(minutes=17)
                ),
            ]
            db.session.add_all(jobs)
            db.session.flush()

            # --- Leads ---
            leads = []
            for i, campaign in enumerate([campaign1, campaign2], start=1):
                for j in range(1, 4):
                    lead = Lead(
                        first_name=f"Lead{i}-{j}",
                        last_name="Seed",
                        email=f"lead{i}{j}@example.com",
                        company=f"Company {i}-{j}",
                        phone=f"555-000{i}{j}",
                        campaign_id=campaign.id,
                        raw_data={"source": "seed", "index": j}
                    )
                    leads.append(lead)
            db.session.add_all(leads)
            db.session.flush()

            # --- Events ---
            event1 = Event(
                source="api",
                tag="campaign_created",
                data={"campaign_id": campaign1.id, "user_id": user1.id},
                type="log"
            )
            event2 = Event(
                source="browser",
                tag="lead_imported",
                data={"lead_id": leads[0].id, "user_id": user2.id},
                type="message"
            )
            db.session.add_all([event1, event2])

            db.session.commit()
            print("Database seeding complete!")
            print(f"Seeded: 2 users, 1 org, 2 campaigns, 4 jobs, 6 leads, 2 events.")

        except Exception as e:
            db.session.rollback()
            print(f"Error during database seeding: {str(e)}")
            raise

def main():
    print("WARNING: This script is deprecated. Use scripts/full_db_reset.py instead for all reset, migration, and seeding operations.")
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