"""
Database operations and cleanup utilities for smoke tests.
"""

from app.models.user import User


def cleanup_test_data(test_email):
    """Clean up test data from database."""
    try:
        # Reset mock system - now uses the simple reset method
        from app.background_services.smoke_tests.mock_apify_client import reset_campaign_counter
        reset_campaign_counter()
        
        # Override DATABASE_URL for local connection
        import sqlalchemy
        from app.core.config import settings
        
        # Use local database with Docker port mapping
        db_url = f"postgresql://postgres:postgres@localhost:15432/fastapi_k8_proto"
        engine = sqlalchemy.create_engine(db_url, pool_pre_ping=True)
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        db = SessionLocal()
        try:
            # Delete test user and related data
            test_user = db.query(User).filter(User.email == test_email).first()
            if test_user:
                print(f"[Cleanup] Removing test user: {test_email}")
                db.delete(test_user)
                db.commit()
                print(f"[Cleanup] Test data cleaned up successfully")
        except Exception as e:
            print(f"[Cleanup] Error during cleanup: {e}")
            db.rollback()
        finally:
            db.close()
    except Exception as e:
        print(f"[Cleanup] Could not connect to database for cleanup: {e}") 