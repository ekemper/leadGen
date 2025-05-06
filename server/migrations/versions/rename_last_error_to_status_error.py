"""rename last_error to status_error

Revision ID: rename_error_col
Revises: combined_initial_migration
Create Date: 2024-03-19 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'rename_error_col'
down_revision = 'combined_initial_migration'
branch_labels = None
depends_on = None

def upgrade():
    # Rename last_error column to status_error
    op.alter_column('campaigns', 'last_error', new_column_name='status_error')

def downgrade():
    # Rename status_error column back to last_error
    op.alter_column('campaigns', 'status_error', new_column_name='last_error') 