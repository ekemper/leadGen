"""Update schema for validation

Revision ID: update_schema_for_validation
Revises: previous_revision
Create Date: 2024-03-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'update_schema_for_validation'
down_revision = 'previous_revision'
branch_labels = None
depends_on = None

def upgrade():
    # Update campaigns table
    op.alter_column('campaigns', 'name',
                    existing_type=sa.String(255),
                    nullable=False)
    op.alter_column('campaigns', 'description',
                    existing_type=sa.Text(),
                    nullable=True)
    op.alter_column('campaigns', 'status',
                    existing_type=sa.String(50),
                    nullable=False,
                    server_default='CREATED')
    op.alter_column('campaigns', 'created_at',
                    existing_type=sa.DateTime(),
                    nullable=False,
                    server_default=sa.text('CURRENT_TIMESTAMP'))
    op.alter_column('campaigns', 'updated_at',
                    existing_type=sa.DateTime(),
                    nullable=False,
                    server_default=sa.text('CURRENT_TIMESTAMP'))
    
    # Update jobs table
    op.alter_column('jobs', 'campaign_id',
                    existing_type=sa.String(36),
                    nullable=False)
    op.alter_column('jobs', 'job_type',
                    existing_type=sa.String(50),
                    nullable=False)
    op.alter_column('jobs', 'status',
                    existing_type=sa.String(50),
                    nullable=False,
                    server_default='PENDING')
    op.alter_column('jobs', 'parameters',
                    existing_type=postgresql.JSON(astext_type=sa.Text()),
                    nullable=True)
    op.alter_column('jobs', 'result',
                    existing_type=postgresql.JSON(astext_type=sa.Text()),
                    nullable=True)
    op.alter_column('jobs', 'error_message',
                    existing_type=sa.Text(),
                    nullable=True)
    op.alter_column('jobs', 'created_at',
                    existing_type=sa.DateTime(),
                    nullable=False,
                    server_default=sa.text('CURRENT_TIMESTAMP'))
    op.alter_column('jobs', 'updated_at',
                    existing_type=sa.DateTime(),
                    nullable=False,
                    server_default=sa.text('CURRENT_TIMESTAMP'))
    
    # Update leads table
    op.alter_column('leads', 'campaign_id',
                    existing_type=sa.String(36),
                    nullable=False)
    op.alter_column('leads', 'first_name',
                    existing_type=sa.String(100),
                    nullable=True)
    op.alter_column('leads', 'last_name',
                    existing_type=sa.String(100),
                    nullable=True)
    op.alter_column('leads', 'email',
                    existing_type=sa.String(255),
                    nullable=True)
    op.alter_column('leads', 'phone',
                    existing_type=sa.String(50),
                    nullable=True)
    op.alter_column('leads', 'company',
                    existing_type=sa.String(255),
                    nullable=True)
    op.alter_column('leads', 'title',
                    existing_type=sa.String(255),
                    nullable=True)
    op.alter_column('leads', 'linkedin_url',
                    existing_type=sa.String(255),
                    nullable=True)
    op.alter_column('leads', 'source_url',
                    existing_type=sa.String(255),
                    nullable=True)
    op.alter_column('leads', 'raw_data',
                    existing_type=postgresql.JSON(astext_type=sa.Text()),
                    nullable=True)
    op.alter_column('leads', 'created_at',
                    existing_type=sa.DateTime(),
                    nullable=False,
                    server_default=sa.text('CURRENT_TIMESTAMP'))
    op.alter_column('leads', 'updated_at',
                    existing_type=sa.DateTime(),
                    nullable=False,
                    server_default=sa.text('CURRENT_TIMESTAMP'))
    
    # Update users table
    op.alter_column('users', 'email',
                    existing_type=sa.String(255),
                    nullable=False)
    op.alter_column('users', 'name',
                    existing_type=sa.String(255),
                    nullable=False)
    op.alter_column('users', 'password',
                    existing_type=sa.String(255),
                    nullable=False)
    op.alter_column('users', 'created_at',
                    existing_type=sa.DateTime(),
                    nullable=False,
                    server_default=sa.text('CURRENT_TIMESTAMP'))
    op.alter_column('users', 'updated_at',
                    existing_type=sa.DateTime(),
                    nullable=False,
                    server_default=sa.text('CURRENT_TIMESTAMP'))

def downgrade():
    # Revert campaigns table
    op.alter_column('campaigns', 'name',
                    existing_type=sa.String(255),
                    nullable=True)
    op.alter_column('campaigns', 'description',
                    existing_type=sa.Text(),
                    nullable=True)
    op.alter_column('campaigns', 'status',
                    existing_type=sa.String(50),
                    nullable=True,
                    server_default=None)
    op.alter_column('campaigns', 'created_at',
                    existing_type=sa.DateTime(),
                    nullable=True,
                    server_default=None)
    op.alter_column('campaigns', 'updated_at',
                    existing_type=sa.DateTime(),
                    nullable=True,
                    server_default=None)
    
    # Revert jobs table
    op.alter_column('jobs', 'campaign_id',
                    existing_type=sa.String(36),
                    nullable=True)
    op.alter_column('jobs', 'job_type',
                    existing_type=sa.String(50),
                    nullable=True)
    op.alter_column('jobs', 'status',
                    existing_type=sa.String(50),
                    nullable=True,
                    server_default=None)
    op.alter_column('jobs', 'parameters',
                    existing_type=postgresql.JSON(astext_type=sa.Text()),
                    nullable=True)
    op.alter_column('jobs', 'result',
                    existing_type=postgresql.JSON(astext_type=sa.Text()),
                    nullable=True)
    op.alter_column('jobs', 'error_message',
                    existing_type=sa.Text(),
                    nullable=True)
    op.alter_column('jobs', 'created_at',
                    existing_type=sa.DateTime(),
                    nullable=True,
                    server_default=None)
    op.alter_column('jobs', 'updated_at',
                    existing_type=sa.DateTime(),
                    nullable=True,
                    server_default=None)
    
    # Revert leads table
    op.alter_column('leads', 'campaign_id',
                    existing_type=sa.String(36),
                    nullable=True)
    op.alter_column('leads', 'first_name',
                    existing_type=sa.String(100),
                    nullable=True)
    op.alter_column('leads', 'last_name',
                    existing_type=sa.String(100),
                    nullable=True)
    op.alter_column('leads', 'email',
                    existing_type=sa.String(255),
                    nullable=True)
    op.alter_column('leads', 'phone',
                    existing_type=sa.String(50),
                    nullable=True)
    op.alter_column('leads', 'company',
                    existing_type=sa.String(255),
                    nullable=True)
    op.alter_column('leads', 'title',
                    existing_type=sa.String(255),
                    nullable=True)
    op.alter_column('leads', 'linkedin_url',
                    existing_type=sa.String(255),
                    nullable=True)
    op.alter_column('leads', 'source_url',
                    existing_type=sa.String(255),
                    nullable=True)
    op.alter_column('leads', 'raw_data',
                    existing_type=postgresql.JSON(astext_type=sa.Text()),
                    nullable=True)
    op.alter_column('leads', 'created_at',
                    existing_type=sa.DateTime(),
                    nullable=True,
                    server_default=None)
    op.alter_column('leads', 'updated_at',
                    existing_type=sa.DateTime(),
                    nullable=True,
                    server_default=None)
    
    # Revert users table
    op.alter_column('users', 'email',
                    existing_type=sa.String(255),
                    nullable=True)
    op.alter_column('users', 'name',
                    existing_type=sa.String(255),
                    nullable=True)
    op.alter_column('users', 'password',
                    existing_type=sa.String(255),
                    nullable=True)
    op.alter_column('users', 'created_at',
                    existing_type=sa.DateTime(),
                    nullable=True,
                    server_default=None)
    op.alter_column('users', 'updated_at',
                    existing_type=sa.DateTime(),
                    nullable=True,
                    server_default=None) 