"""initial combined migration

Revision ID: combined_initial_migration
Revises: 
Create Date: 2024-03-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'combined_initial_migration'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create event source and type enums first
    op.execute("CREATE TYPE event_source AS ENUM ('browser', 'api', 'database')")
    op.execute("CREATE TYPE event_type AS ENUM ('error', 'message', 'log')")

    # Create users table
    op.create_table('users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(254), unique=True, nullable=False),
        sa.Column('password', sa.LargeBinary, nullable=False),
        sa.Column('failed_attempts', sa.Integer, server_default='0'),
        sa.Column('last_failed_attempt', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False)
    )

    # Create organizations table
    op.create_table('organizations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False)
    )

    # Create campaigns table
    op.create_table('campaigns',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('status', sa.String(50), server_default='created', nullable=False),
        sa.Column('status_message', sa.Text(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('job_status', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('job_ids', postgresql.JSON(astext_type=sa.Text()), nullable=True)
    )

    # Create leads table
    op.create_table('leads',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), server_default='', nullable=False),
        sa.Column('email', sa.String(255), server_default='', nullable=False),
        sa.Column('company_name', sa.String(255), server_default=''),
        sa.Column('phone', sa.String(50), server_default=''),
        sa.Column('status', sa.String(50), server_default='new'),
        sa.Column('source', sa.String(50), server_default='apollo'),
        sa.Column('notes', sa.Text(), server_default=''),
        sa.Column('campaign_id', sa.String(36), sa.ForeignKey('campaigns.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('raw_lead_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('email_verification', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('enrichment_results', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('email_copy', sa.Text(), nullable=True)
    )

    # Create events table
    op.create_table('events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('source', sa.Enum('browser', 'api', 'database', name='event_source'), nullable=False),
        sa.Column('tag', sa.String(255), nullable=False),
        sa.Column('data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('type', sa.Enum('error', 'message', 'log', name='event_type'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False)
    )

def downgrade():
    # Drop tables in reverse order
    op.drop_table('events')
    op.drop_table('leads')
    op.drop_table('campaigns')
    op.drop_table('organizations')
    op.drop_table('users')
    
    # Drop enums
    op.execute('DROP TYPE event_source')
    op.execute('DROP TYPE event_type') 