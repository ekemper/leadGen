"""add lead model

Revision ID: a99f26548ab8
Revises: c84cc26cd3a2
Create Date: 2025-05-26 22:11:58.613667

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a99f26548ab8'
down_revision: Union[str, None] = 'c84cc26cd3a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('leads',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('campaign_id', sa.String(length=36), nullable=False),
    sa.Column('first_name', sa.String(length=100), nullable=True),
    sa.Column('last_name', sa.String(length=100), nullable=True),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('phone', sa.String(length=50), nullable=True),
    sa.Column('company', sa.String(length=255), nullable=True),
    sa.Column('title', sa.String(length=255), nullable=True),
    sa.Column('linkedin_url', sa.String(length=255), nullable=True),
    sa.Column('source_url', sa.String(length=255), nullable=True),
    sa.Column('raw_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
    sa.Column('email_verification', postgresql.JSON(astext_type=sa.Text()), nullable=True),
    sa.Column('enrichment_results', postgresql.JSON(astext_type=sa.Text()), nullable=True),
    sa.Column('enrichment_job_id', sa.String(length=36), nullable=True),
    sa.Column('email_copy_gen_results', postgresql.JSON(astext_type=sa.Text()), nullable=True),
    sa.Column('instantly_lead_record', postgresql.JSON(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_leads_id'), 'leads', ['id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_leads_id'), table_name='leads')
    op.drop_table('leads')
    # ### end Alembic commands ###
