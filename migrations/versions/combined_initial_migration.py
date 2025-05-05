"""combined initial migration

Revision ID: combined_initial_migration
Revises: 
Create Date: 2024-03-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = 'combined_initial_migration'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Drop all existing tables first
    conn = op.get_bind()
    conn.execute(text('DROP TABLE IF EXISTS events CASCADE'))
    conn.execute(text('DROP TABLE IF EXISTS leads CASCADE'))
    conn.execute(text('DROP TABLE IF EXISTS users CASCADE'))
    conn.execute(text('DROP TABLE IF EXISTS campaigns CASCADE'))
    conn.execute(text('DROP TABLE IF EXISTS organizations CASCADE'))
    conn.execute(text('DROP TYPE IF EXISTS event_source'))
    conn.execute(text('DROP TYPE IF EXISTS event_type'))
    
    # Create organizations table
    op.create_table('organizations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create campaigns table with organization relationship
    op.create_table('campaigns',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='created'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create users table
    op.create_table('users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=254), nullable=False),
        sa.Column('password', sa.LargeBinary(), nullable=False),
        sa.Column('failed_attempts', sa.Integer(), nullable=True),
        sa.Column('last_failed_attempt', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    # Create leads table with all fields including email_copy
    op.create_table('leads',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('company_name', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('campaign_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('raw_lead_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('email_verification', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('enrichment_results', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('email_copy', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create events table with string columns instead of enums
    op.create_table('events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('tag', sa.String(length=255), nullable=False),
        sa.Column('data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Add check constraints to ensure valid values
    conn = op.get_bind()
    conn.execute(text("ALTER TABLE events ADD CONSTRAINT event_source_check CHECK (source IN ('browser', 'api', 'database'))"))
    conn.execute(text("ALTER TABLE events ADD CONSTRAINT event_type_check CHECK (type IN ('error', 'message', 'log'))"))


def downgrade():
    # Drop all tables
    op.drop_table('events')
    op.drop_table('leads')
    op.drop_table('users')
    op.drop_table('campaigns')
    op.drop_table('organizations')
    
    # Drop custom types
    conn = op.get_bind()
    conn.execute(text('DROP TYPE IF EXISTS event_source'))
    conn.execute(text('DROP TYPE IF EXISTS event_type')) 