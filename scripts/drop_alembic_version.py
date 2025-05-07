import os
from sqlalchemy import create_engine, text

conn_str = os.environ.get('NEON_CONNECTION_STRING')
if not conn_str:
    raise RuntimeError('NEON_CONNECTION_STRING environment variable not set')

engine = create_engine(conn_str)

with engine.connect() as conn:
    conn.execute(text('DROP TABLE IF EXISTS alembic_version'))
    print('Dropped alembic_version table.') 