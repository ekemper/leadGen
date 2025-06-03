"""Remove deprecated job types from JobType enum

Revision ID: 2a500d56a800
Revises: b19d5995b29c
Create Date: 2025-05-30 23:43:26.933822

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a500d56a800'
down_revision: Union[str, None] = 'b19d5995b29c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove deprecated job types from the JobType enum.
    
    Since PostgreSQL doesn't support dropping enum values directly,
    we need to recreate the enum with only the valid values.
    """
    connection = op.get_bind()
    
    # First, check if there are any jobs with deprecated types and migrate them
    # Migrate any GENERAL jobs to FETCH_LEADS
    connection.execute(sa.text("UPDATE jobs SET job_type = 'FETCH_LEADS' WHERE job_type = 'GENERAL'"))
    
    # Migrate any other deprecated types to ENRICH_LEAD as they're all part of lead processing
    deprecated_types = ['VERIFY_EMAILS', 'GENERATE_EMAIL_COPY', 'UPLOAD_TO_INSTANTLY', 'ENRICH_LEADS']
    for dep_type in deprecated_types:
        connection.execute(sa.text(f"UPDATE jobs SET job_type = 'ENRICH_LEAD' WHERE job_type = '{dep_type}'"))
    
    # Create new enum with only valid values
    connection.execute(sa.text("CREATE TYPE jobtype_new AS ENUM ('FETCH_LEADS', 'ENRICH_LEAD', 'CLEANUP_CAMPAIGN')"))
    
    # Drop the default constraint temporarily
    connection.execute(sa.text("ALTER TABLE jobs ALTER COLUMN job_type DROP DEFAULT"))
    
    # Update the jobs table to use the new enum
    connection.execute(sa.text("ALTER TABLE jobs ALTER COLUMN job_type TYPE jobtype_new USING job_type::text::jobtype_new"))
    
    # Set the new default value
    connection.execute(sa.text("ALTER TABLE jobs ALTER COLUMN job_type SET DEFAULT 'FETCH_LEADS'::jobtype_new"))
    
    # Drop the old enum and rename the new one
    connection.execute(sa.text("DROP TYPE jobtype"))
    connection.execute(sa.text("ALTER TYPE jobtype_new RENAME TO jobtype"))


def downgrade() -> None:
    """
    Restore the old enum with deprecated values.
    
    This recreates the enum with all the original values for rollback purposes.
    """
    connection = op.get_bind()
    
    # Create enum with all original values (including deprecated ones)
    original_values = [
        'CLEANUP_CAMPAIGN', 'ENRICH_LEAD', 'ENRICH_LEADS', 'FETCH_LEADS', 
        'GENERAL', 'GENERATE_EMAIL_COPY', 'UPLOAD_TO_INSTANTLY', 'VERIFY_EMAILS'
    ]
    enum_values = "'" + "', '".join(original_values) + "'"
    connection.execute(sa.text(f"CREATE TYPE jobtype_old AS ENUM ({enum_values})"))
    
    # Drop the default constraint temporarily
    connection.execute(sa.text("ALTER TABLE jobs ALTER COLUMN job_type DROP DEFAULT"))
    
    # Update the jobs table to use the old enum
    connection.execute(sa.text("ALTER TABLE jobs ALTER COLUMN job_type TYPE jobtype_old USING job_type::text::jobtype_old"))
    
    # Set the old default value
    connection.execute(sa.text("ALTER TABLE jobs ALTER COLUMN job_type SET DEFAULT 'GENERAL'::jobtype_old"))
    
    # Drop the new enum and rename the old one back
    connection.execute(sa.text("DROP TYPE jobtype"))
    connection.execute(sa.text("ALTER TYPE jobtype_old RENAME TO jobtype"))
