import os
import json
import time
import tempfile
import shutil
from datetime import datetime
import pytest
from server.utils.logging_config import browser_logger, combined_logger, setup_logger

class TestLogging:
    """Test suite for logging functionality."""

    @pytest.fixture(autouse=True)
    def setup_test_logs(self):
        """Setup temporary log directory for tests."""
        # Create a temporary directory
        self.test_log_dir = tempfile.mkdtemp()
        
        # Create test loggers with the temporary directory
        self.test_browser_logger = setup_logger('browser', os.path.join(self.test_log_dir, 'browser.log'))
        self.test_combined_logger = setup_logger('combined', os.path.join(self.test_log_dir, 'combined.log'))
        
        yield
        
        # Cleanup
        shutil.rmtree(self.test_log_dir)

    def test_browser_log_format(self):
        """Test that browser logs are properly formatted with required fields."""
        # Create a test log entry
        test_log = {
            'level': 'INFO',
            'data': [],
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'browser'
        }
        
        # Log the test entry
        self.test_browser_logger.info("Test browser log", extra=test_log)
        
        # Give some time for the log to be written
        time.sleep(0.1)
        
        # Read the log file
        with open(os.path.join(self.test_log_dir, 'browser.log'), 'r') as f:
            lines = f.readlines()
            assert len(lines) > 0, "Log file is empty"
            log_entry = json.loads(lines[-1])
        
        # Verify required fields
        assert 'timestamp' in log_entry
        assert 'level' in log_entry
        assert 'message' in log_entry
        assert 'source' in log_entry
        assert log_entry['source'] == 'browser'
        assert log_entry['level'] == 'INFO'
        assert log_entry['message'] == 'Test browser log'

    def test_real_time_logging(self):
        """Test that logs are properly synchronized between browser and combined logs."""
        # Create a test log entry
        test_log = {
            'level': 'INFO',
            'data': [],
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'browser'
        }
        
        # Log the test entry to both loggers
        test_message = "Test real-time log"
        self.test_browser_logger.info(test_message, extra=test_log)
        self.test_combined_logger.info(test_message, extra=test_log)
        
        # Give some time for the log to be written
        time.sleep(0.1)
        
        # Read both log files
        with open(os.path.join(self.test_log_dir, 'browser.log'), 'r') as f:
            browser_logs = f.readlines()
            assert len(browser_logs) > 0, "Browser log file is empty"
        
        with open(os.path.join(self.test_log_dir, 'combined.log'), 'r') as f:
            combined_logs = f.readlines()
            assert len(combined_logs) > 0, "Combined log file is empty"
        
        # Get the last entries that are not initialization messages
        browser_entry = None
        for line in reversed(browser_logs):
            entry = json.loads(line)
            if entry['message'] == test_message:
                browser_entry = entry
                break
        assert browser_entry is not None, "No test log entry found in browser.log"
        
        combined_entry = None
        for line in reversed(combined_logs):
            entry = json.loads(line)
            if entry['message'] == test_message:
                combined_entry = entry
                break
        assert combined_entry is not None, "No test log entry found in combined.log"
        
        # Verify entries match
        assert browser_entry['message'] == combined_entry['message']
        assert browser_entry['level'] == combined_entry['level']
        assert browser_entry['source'] == combined_entry['source']
        assert browser_entry['timestamp'] == combined_entry['timestamp']

    def test_log_sanitization(self):
        """Test that sensitive data is properly sanitized in logs."""
        # Create a test log entry with sensitive data
        test_log = {
            'level': 'INFO',
            'data': {
                'email': 'test@example.com',
                'password': 'secret123',
                'api_key': 'sk_test_123456'
            },
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'browser'
        }
        
        # Log the test entry
        self.test_browser_logger.info("Test log with sensitive data", extra=test_log)
        
        # Give some time for the log to be written
        time.sleep(0.1)
        
        # Read the log file
        with open(os.path.join(self.test_log_dir, 'browser.log'), 'r') as f:
            lines = f.readlines()
            assert len(lines) > 0, "Log file is empty"
            log_entry = json.loads(lines[-1])
        
        # Verify sensitive data is sanitized with specific redaction messages
        assert log_entry['data']['email'] == '[REDACTED_EMAIL]'
        assert log_entry['data']['password'] == '[REDACTED_PASSWORD]'
        assert log_entry['data']['api_key'] == '[REDACTED_API_KEY]' 