import pytest
import os
import shutil
from server.utils.logging_config import LOG_DIR

@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    """Set up logging for tests."""
    # Create test logs directory
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    
    yield
    
    # Clean up
    if os.path.exists(LOG_DIR):
        shutil.rmtree(LOG_DIR) 