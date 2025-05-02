"""update lead model: rename company to company_name, add raw_lead_data JSON column

Revision ID: 20240502_01
Revises: 
Create Date: 2025-05-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20240502_01'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Rename 'company' to 'company_name'
    with op.batch_alter_table('leads') as batch_op:
        batch_op.alter_column('company', new_column_name='company_name', existing_type=sa.String(length=255))
        batch_op.add_column(sa.Column('raw_lead_data', postgresql.JSON(), nullable=True))

def downgrade():
    with op.batch_alter_table('leads') as batch_op:
        batch_op.alter_column('company_name', new_column_name='company', existing_type=sa.String(length=255))
        batch_op.drop_column('raw_lead_data') 