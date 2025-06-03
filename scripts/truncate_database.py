#!/usr/bin/env python3
"""
Database Truncation Script

This script truncates the leads, jobs, and campaigns tables from the database.
It's designed to be run inside the Docker container where it has access to the
running database instance.

Usage:
    python scripts/truncate_database.py

Warning: This operation is IRREVERSIBLE and will delete ALL data from the
specified tables. Use with extreme caution!
"""

import os
import sys
import logging
from pathlib import Path

# Add the parent directory to the Python path so we can import from app
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def confirm_truncation():
    """
    Prompt user for confirmation before proceeding with truncation.
    Returns True if user confirms, False otherwise.
    """
    print("⚠️  WARNING: This will permanently delete ALL data from the following tables:")
    print("   - leads")
    print("   - jobs") 
    print("   - campaigns")
    print()
    print("This operation is IRREVERSIBLE!")
    print()
    
    # In a Docker container, we might not have interactive input
    # Check if we're running interactively
    if not sys.stdin.isatty():
        logger.warning("Running in non-interactive mode. Set CONFIRM_TRUNCATE=yes to proceed.")
        return os.getenv('CONFIRM_TRUNCATE', '').lower() == 'yes'
    
    while True:
        response = input("Are you sure you want to continue? (yes/no): ").lower().strip()
        if response in ['yes', 'y']:
            return True
        elif response in ['no', 'n']:
            return False
        else:
            print("Please enter 'yes' or 'no'")

def truncate_tables():
    """
    Truncate the leads, jobs, and campaigns tables.
    Uses TRUNCATE CASCADE to handle foreign key constraints.
    """
    try:
        # Create database engine
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        
        logger.info("Connecting to database...")
        logger.info(f"Database URL: {settings.DATABASE_URL}")
        
        with engine.connect() as connection:
            # Start a transaction
            trans = connection.begin()
            
            try:
                # Disable foreign key checks temporarily (if needed)
                # Note: PostgreSQL doesn't have a global way to disable FK checks
                # but TRUNCATE CASCADE will handle the relationships
                
                logger.info("Starting truncation process...")
                
                # Truncate tables in order that respects foreign key constraints
                # Leads first (has FK to campaigns)
                logger.info("Truncating leads table...")
                connection.execute(text("TRUNCATE TABLE leads CASCADE"))
                
                # Jobs next (has FK to campaigns)
                logger.info("Truncating jobs table...")
                connection.execute(text("TRUNCATE TABLE jobs CASCADE"))
                
                # Campaigns last (referenced by leads and jobs)
                logger.info("Truncating campaigns table...")
                connection.execute(text("TRUNCATE TABLE campaigns CASCADE"))
                
                # Commit the transaction
                trans.commit()
                logger.info("✅ Successfully truncated all tables!")
                
            except Exception as e:
                # Rollback on error
                trans.rollback()
                logger.error(f"❌ Error during truncation: {str(e)}")
                raise
                
    except Exception as e:
        logger.error(f"❌ Failed to connect to database or execute truncation: {str(e)}")
        raise

def verify_truncation():
    """
    Verify that the tables have been truncated by checking row counts.
    """
    try:
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        
        with engine.connect() as connection:
            # Check row counts
            tables = ['leads', 'jobs', 'campaigns']
            
            logger.info("Verifying truncation...")
            for table in tables:
                result = connection.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                logger.info(f"Table '{table}': {count} rows remaining")
                
                if count > 0:
                    logger.warning(f"⚠️  Table '{table}' still has {count} rows!")
                else:
                    logger.info(f"✅ Table '{table}' is empty")
                    
    except Exception as e:
        logger.error(f"❌ Failed to verify truncation: {str(e)}")
        raise

def main():
    """
    Main function that orchestrates the truncation process.
    """
    logger.info("Database Truncation Script Started")
    logger.info("=" * 50)
    
    try:
        # Confirm with user
        if not confirm_truncation():
            logger.info("Truncation cancelled by user.")
            return
        
        # Perform truncation
        truncate_tables()
        
        # Verify the operation
        verify_truncation()
        
        logger.info("=" * 50)
        logger.info("Database truncation completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Script failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 