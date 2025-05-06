"""add updated_at to campaigns

Revision ID: add_updated_at
Revises: rename_error_col
Create Date: 2024-03-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'add_updated_at'
down_revision = 'rename_error_col'
branch_labels = None
depends_on = None

def upgrade():
    # Add updated_at column with current timestamp as default
    op.add_column('campaigns', 
        sa.Column('updated_at', 
            sa.DateTime(), 
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False
        )
    )
    
    # Add trigger to automatically update updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    op.execute("""
        CREATE TRIGGER update_campaigns_updated_at
            BEFORE UPDATE ON campaigns
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)

def downgrade():
    # Drop the trigger first
    op.execute("DROP TRIGGER IF EXISTS update_campaigns_updated_at ON campaigns")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    
    # Then drop the column
    op.drop_column('campaigns', 'updated_at') 