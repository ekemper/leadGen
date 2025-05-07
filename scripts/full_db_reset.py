"""
full_db_reset.py

Drops and recreates the public schema, removes all enum types, resets Alembic migration state, and can optionally seed the database.
**WARNING: This will delete ALL data and schema in the database.**

Usage:
    export NEON_CONNECTION_STRING=...
    python scripts/full_db_reset.py [--force] [--stamp-head] [--seed]

Options:
    --force       Skip confirmation prompt (for CI)
    --stamp-head  Stamp Alembic to head after reset
    --seed        Seed the database with initial data (calls reset_migrate_seed.py:seed_database)

Recommended for development and CI only.
"""
import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import subprocess

# Import seeding logic
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/../'))
try:
    from reset_migrate_seed import seed_database
    from server.app import create_app
    from server.config.database import db
except ImportError:
    seed_database = None

conn_str = os.environ.get('NEON_CONNECTION_STRING')
if not conn_str:
    print('ERROR: NEON_CONNECTION_STRING environment variable not set')
    sys.exit(1)

force = '--force' in sys.argv
stamp_head = '--stamp-head' in sys.argv
seed = '--seed' in sys.argv

if not force:
    confirm = input('This will DROP ALL TABLES, ENUMS, AND MIGRATION STATE in the database. Are you sure? (y/N): ')
    if confirm.lower() != 'y':
        print('Aborted.')
        sys.exit(0)

try:
    conn = psycopg2.connect(conn_str)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    with conn.cursor() as cur:
        print('Dropping and recreating public schema...')
        cur.execute('DROP SCHEMA public CASCADE')
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

if stamp_head:
    print('Stamping Alembic to head...')
    result = subprocess.run(['flask', 'db', 'stamp', 'head'], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        sys.exit(result.returncode)

if seed:
    print('Seeding the database with initial data...')
    if seed_database is None:
        print('ERROR: Could not import seed_database from reset_migrate_seed.py. Seeding aborted.')
        sys.exit(1)
    try:
        # Create Flask app and seed
        app = create_app()
        seed_database(app)
        print('Database seeding complete!')
    except Exception as e:
        print(f'ERROR during seeding: {e}')
        sys.exit(1)

print('Done.') 