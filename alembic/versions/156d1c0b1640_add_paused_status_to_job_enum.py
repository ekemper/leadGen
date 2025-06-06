"""add_paused_status_to_job_enum

Revision ID: 156d1c0b1640
Revises: 66cdab1a3a75
Create Date: 2025-06-02 01:12:15.591123

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '156d1c0b1640'
down_revision: Union[str, None] = '66cdab1a3a75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    # Add PAUSED status to JobStatus enum
    connection = op.get_bind()
    
    # Check if PAUSED enum value already exists before adding it
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_enum 
            WHERE enumlabel = 'paused' 
            AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'jobstatus')
        )
    """)).scalar()
    
    # Only add the enum value if it doesn't exist
    if not result:
        connection.execute(sa.text("ALTER TYPE jobstatus ADD VALUE 'paused'"))
        connection.commit()
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    # Note: PostgreSQL doesn't support removing enum values directly.
    # This would require recreating the enum type, which is complex in production.
    # For safety, we'll leave the enum value but update any paused jobs to pending.
    connection = op.get_bind()
    
    # Update any paused jobs back to pending
    connection.execute(sa.text("UPDATE jobs SET status = 'pending' WHERE status = 'paused'"))
    connection.commit()
    # ### end Alembic commands ###
