"""fix_paused_status_case_consistency

Revision ID: 1c3d495e314c
Revises: 156d1c0b1640
Create Date: 2025-06-02 19:00:00.612082

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1c3d495e314c'
down_revision: Union[str, None] = '156d1c0b1640'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Fix case inconsistency in JobStatus enum:
    - Add 'PAUSED' enum value (uppercase) to match existing pattern
    - Update any existing jobs with status 'paused' to 'PAUSED'
    - Remove the lowercase 'paused' enum value
    """
    connection = op.get_bind()
    
    # Step 1: Add the correct uppercase 'PAUSED' enum value FIRST
    # Check if PAUSED enum value already exists before adding it
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_enum 
            WHERE enumlabel = 'PAUSED' 
            AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'jobstatus')
        )
    """)).scalar()
    
    if not result:
        connection.execute(sa.text("ALTER TYPE jobstatus ADD VALUE 'PAUSED'"))
        # Commit here so the new enum value can be used immediately
        connection.commit()
    
    # Step 2: Check if lowercase 'paused' exists before trying to update it
    paused_exists = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_enum 
            WHERE enumlabel = 'paused' 
            AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'jobstatus')
        )
    """)).scalar()
    
    # Only update jobs if lowercase 'paused' enum value exists
    if paused_exists:
        # Update any existing jobs from 'paused' to 'PAUSED'
        connection.execute(sa.text(
            "UPDATE jobs SET status = 'PAUSED' WHERE status = 'paused'"
        ))
        
        # Step 3: Remove the incorrect lowercase 'paused' enum value
        # Create new enum type with correct values
        connection.execute(sa.text("""
            CREATE TYPE jobstatus_new AS ENUM (
                'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED', 'PAUSED'
            )
        """))
        
        # Update the jobs table to use the new enum type
        connection.execute(sa.text("""
            ALTER TABLE jobs 
            ALTER COLUMN status TYPE jobstatus_new 
            USING status::text::jobstatus_new
        """))
        
        # Drop the old enum type and rename the new one
        connection.execute(sa.text("DROP TYPE jobstatus"))
        connection.execute(sa.text("ALTER TYPE jobstatus_new RENAME TO jobstatus"))
    
    connection.commit()


def downgrade() -> None:
    """
    Rollback the case fix by reverting to the mixed-case enum.
    This recreates the original inconsistent state for rollback purposes.
    """
    connection = op.get_bind()
    
    # Update any PAUSED jobs back to paused (lowercase)
    connection.execute(sa.text(
        "UPDATE jobs SET status = 'paused' WHERE status = 'PAUSED'"
    ))
    
    # Recreate the original mixed-case enum
    connection.execute(sa.text("""
        CREATE TYPE jobstatus_old AS ENUM (
            'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED', 'paused'
        )
    """))
    
    # Update the table to use the old enum
    connection.execute(sa.text("""
        ALTER TABLE jobs 
        ALTER COLUMN status TYPE jobstatus_old 
        USING status::text::jobstatus_old
    """))
    
    # Replace the enum type
    connection.execute(sa.text("DROP TYPE jobstatus"))
    connection.execute(sa.text("ALTER TYPE jobstatus_old RENAME TO jobstatus"))
    
    connection.commit()
