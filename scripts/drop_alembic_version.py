import os
from sqlalchemy import create_engine, text

conn_str = os.environ.get('DATABASE_URL')
if not conn_str:
    raise RuntimeError('DATABASE_URL environment variable not set')

engine = create_engine(conn_str)

with engine.connect() as conn:
    conn.execute(text('DROP TABLE IF EXISTS alembic_version'))
    print('Dropped alembic_version table.') 