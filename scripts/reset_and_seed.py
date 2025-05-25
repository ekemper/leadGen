#!/usr/bin/env python3
"""
reset_and_seed.py

Unified script for local database management: reset, migrate, and seed.

Usage:
    python scripts/reset_and_seed.py [--fresh-migrations] [--seed-only]

Docker:
    docker compose exec backend python scripts/reset_and_seed.py [--fresh-migrations] [--seed-only]

Options:
    --fresh-migrations   Delete all migration files and generate a new initial migration
    --seed-only          Only seed the database (no reset or migration)

WARNING: This will irreversibly delete all data in your database!
"""
import os
import sys
import subprocess
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Import seeding logic
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/../'))
from scripts.seed_logic import seed_database
from server.app import create_app

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), '../migrations/versions')


def confirm_or_exit():
    print("\n*** DANGER: This will DELETE ALL data in your database! ***")
    confirm = input("Type 'yes' to continue: ")
    if confirm.strip().lower() != 'yes':
        print("Aborted.")
        sys.exit(0)

def delete_migration_files():
    print(f"Deleting all migration files in {MIGRATIONS_DIR} ...")
    for fname in os.listdir(MIGRATIONS_DIR):
        if fname.endswith('.py') and not fname.startswith('__'):
            os.remove(os.path.join(MIGRATIONS_DIR, fname))
    print("Migration files deleted.")

def run_cmd(cmd, env=None):
    print(f"\n$ {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        sys.exit(result.returncode)

def reset_database():
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
    conn_str = os.environ.get('DATABASE_URL')
    if not conn_str:
        print('ERROR: DATABASE_URL environment variable not set')
        sys.exit(1)
    try:
        conn = psycopg2.connect(conn_str)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        with conn.cursor() as cur:
            print("Explicitly dropping 'events' table in all schemas (if exists)...")
            cur.execute("""
                DO $$ DECLARE
                    r RECORD;
                BEGIN
                    FOR r IN (SELECT schemaname, tablename FROM pg_tables WHERE tablename = 'events' AND schemaname NOT IN ('pg_catalog', 'information_schema')) LOOP
                        EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.schemaname) || '.' || quote_ident(r.tablename) || ' CASCADE';
                    END LOOP;
                END $$;
            """)
            print('Aggressively dropping all tables, views, and sequences in all schemas...')
            cur.execute("""
                DO $$ DECLARE
                    r RECORD;
                BEGIN
                    -- Drop all tables
                    FOR r IN (SELECT tablename, schemaname FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema')) LOOP
                        EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.schemaname) || '.' || quote_ident(r.tablename) || ' CASCADE';
                    END LOOP;
                    -- Drop all views
                    FOR r IN (SELECT table_name, table_schema FROM information_schema.views WHERE table_schema NOT IN ('pg_catalog', 'information_schema')) LOOP
                        EXECUTE 'DROP VIEW IF EXISTS ' || quote_ident(r.table_schema) || '.' || quote_ident(r.table_name) || ' CASCADE';
                    END LOOP;
                    -- Drop all sequences
                    FOR r IN (SELECT sequence_name, sequence_schema FROM information_schema.sequences WHERE sequence_schema NOT IN ('pg_catalog', 'information_schema')) LOOP
                        EXECUTE 'DROP SEQUENCE IF EXISTS ' || quote_ident(r.sequence_schema) || '.' || quote_ident(r.sequence_name) || ' CASCADE';
                    END LOOP;
                END $$;
            """)
            print('Dropping and recreating public schema...')
            cur.execute('DROP SCHEMA IF EXISTS public CASCADE')
            cur.execute('CREATE SCHEMA public')
            print('Dropping all enum types...')
            cur.execute("""
                DO $$
                DECLARE
                    r RECORD;
                BEGIN
                    FOR r IN (SELECT n.nspname, t.typname FROM pg_type t
                              JOIN pg_enum e ON t.oid = e.enumtypid
                              JOIN pg_namespace n ON n.oid = t.typnamespace)
                    LOOP
                        EXECUTE 'DROP TYPE IF EXISTS ' || quote_ident(r.nspname) || '.' || quote_ident(r.typname) || ' CASCADE';
                    END LOOP;
                END$$;
            """)
            print('Dropping alembic_version table if exists...')
            cur.execute('DROP TABLE IF EXISTS alembic_version')
        conn.close()
        print('Database schema, enums, and alembic_version table fully reset.')
    except Exception as e:
        print(f'ERROR: {e}')
        sys.exit(1)

def migrate_database(fresh_migrations):
    if fresh_migrations:
        delete_migration_files()
        run_cmd(['flask', 'db', 'migrate', '-m', 'Initial migration'], env={**os.environ, 'FLASK_APP': 'server.app:create_app'})
    run_cmd(['flask', 'db', 'upgrade'], env={**os.environ, 'FLASK_APP': 'server.app:create_app'})

def seed_db():
    print("Seeding the database with initial data...")
    try:
        app = create_app()
        seed_database(app)
        print("Database seeding complete!")
    except Exception as e:
        print(f"Error during database seeding: {e}")
        sys.exit(1)

def main():
    fresh_migrations = '--fresh-migrations' in sys.argv
    seed_only = '--seed-only' in sys.argv
    no_prompt = '--no-prompt' in sys.argv

    if seed_only:
        seed_db()
        return

    if not no_prompt:
        confirm_or_exit()

    # Step 1: Reset DB
    reset_database()

    # Step 2: Migrate DB
    migrate_database(fresh_migrations)

    # Step 3: Seed DB
    seed_db()

    print("\nDone. Database reset, migrated, and seeded.")

if __name__ == '__main__':
    main() 