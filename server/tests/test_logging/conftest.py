import os
import pytest
from server.utils.logging_config import LOG_DIR

@pytest.fixture(autouse=True)
def setup_logs():
    """Setup and cleanup log files before and after tests."""
    # Create logs directory if it doesn't exist
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    
    # Ensure log files exist
    for log_file in ['browser.log', 'combined.log']:
        log_path = os.path.join(LOG_DIR, log_file)
        if not os.path.exists(log_path):
            open(log_path, 'a').close()
    
    yield
    
    # Clean up log files after tests
    for log_file in ['browser.log', 'combined.log']:
        log_path = os.path.join(LOG_DIR, log_file)
        if os.path.exists(log_path):
            os.remove(log_path) 