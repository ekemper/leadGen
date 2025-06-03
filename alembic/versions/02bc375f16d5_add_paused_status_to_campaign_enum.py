"""add_paused_status_to_campaign_enum

Revision ID: 02bc375f16d5
Revises: 1c3d495e314c
Create Date: 2025-06-02 19:06:14.798290

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '02bc375f16d5'
down_revision: Union[str, None] = '1c3d495e314c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add PAUSED status to CampaignStatus enum.
    """
    connection = op.get_bind()
    
    # Check if PAUSED enum value already exists before adding it
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_enum 
            WHERE enumlabel = 'PAUSED' 
            AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'campaignstatus')
        )
    """)).scalar()
    
    # Only add the enum value if it doesn't exist
    if not result:
        connection.execute(sa.text("ALTER TYPE campaignstatus ADD VALUE 'PAUSED'"))
        connection.commit()


def downgrade() -> None:
    """
    Rollback PAUSED status addition.
    Note: PostgreSQL doesn't support removing enum values directly.
    This will update any paused campaigns back to created status.
    """
    connection = op.get_bind()
    
    # Update any paused campaigns back to created
    connection.execute(sa.text("UPDATE campaigns SET status = 'CREATED' WHERE status = 'PAUSED'"))
    connection.commit()
