"""
full_db_reset.py

Drops and recreates the public schema, removes all enum types, resets Alembic migration state, runs all migrations, and seeds the database with initial data.
**WARNING: This will delete ALL data and schema in the database.**

Usage:
    export NEON_CONNECTION_STRING=...
    # or set NEON_CONNECTION_STRING in a .env file in the project root
    python scripts/full_db_reset.py [--force]

Options:
    --force       Skip confirmation prompt (for CI)

Behavior:
    - Loads NEON_CONNECTION_STRING from the environment or .env file
    - Drops and recreates the public schema and all enums
    - Removes the alembic_version table
    - Runs all migrations (flask db upgrade)
    - Seeds the database with initial data

Recommended for development and CI only.
"""
import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import subprocess

# Import seeding logic
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/../'))
try:
    from scripts.reset_migrate_seed import seed_database
    from server.app import create_app
    from server.config.database import db
except ImportError:
    seed_database = None

# Load environment variables from .env if not already set
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

conn_str = os.environ.get('NEON_CONNECTION_STRING')
if not conn_str:
    print('ERROR: NEON_CONNECTION_STRING environment variable not set')
    sys.exit(1)

force = '--force' in sys.argv

if not force:
    confirm = input('This will DROP ALL TABLES, ENUMS, AND MIGRATION STATE in the database. Are you sure? (y/N): ')
    if confirm.lower() != 'y':
        print('Aborted.')
        sys.exit(0)

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
        # Drop all tables
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

# Always run migrations after reset
print('Running migrations (flask db upgrade)...')
result = subprocess.run([
    'flask', 'db', 'upgrade'
], capture_output=True, text=True, env={**os.environ, 'FLASK_APP': 'server.app:create_app'})
print(result.stdout)
if result.returncode != 0:
    print(result.stderr)
    sys.exit(result.returncode)

# Always seed the database after migrations
print('Seeding the database with initial data...')
if seed_database is None:
    print('ERROR: Could not import seed_database from reset_migrate_seed.py. Seeding aborted.')
    sys.exit(1)
try:
    app = create_app()
    seed_database(app)
    print('Database seeding complete!')
except Exception as e:
    print(f'ERROR during seeding: {e}')
    sys.exit(1)

print('Done.') 