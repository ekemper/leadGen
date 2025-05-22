import os
import json
import time
import tempfile
import shutil
from datetime import datetime
import pytest
from server.utils.logging_config import setup_logger, ContextLogger, LogSanitizer

class TestLogging:
    """Test suite for logging functionality."""

    @pytest.fixture(autouse=True)
    def setup_test_logs(self):
        """Setup temporary log directory for tests."""
        # Create a temporary directory
        self.test_log_dir = tempfile.mkdtemp()
        os.environ['LOG_DIR'] = self.test_log_dir
        
        # Create test logger
        self.test_logger = setup_logger('test')
        
        yield
        
        # Cleanup
        shutil.rmtree(self.test_log_dir)

    def test_log_format(self):
        """Test that logs are properly formatted with required fields."""
        test_message = "Test log message"
        test_context = {'request_id': '123', 'user_id': '456'}
        test_metadata = {'operation': 'test', 'duration_ms': 100}
        
        with ContextLogger(self.test_logger, **test_context):
            self.test_logger.info(test_message, extra={'metadata': test_metadata})
        
        # Give some time for the log to be written
        time.sleep(0.1)
        
        # Read the log file
        with open(os.path.join(self.test_log_dir, 'test.log'), 'r') as f:
            lines = f.readlines()
            assert len(lines) > 0, "Log file is empty"
            log_entry = json.loads(lines[-1])
        
        # Verify required fields
        assert 'timestamp' in log_entry
        assert 'level' in log_entry
        assert 'message' in log_entry
        assert 'source' in log_entry
        assert 'context' in log_entry
        assert 'metadata' in log_entry
        
        # Verify field values
        assert log_entry['level'] == 'INFO'
        assert log_entry['message'] == test_message
        assert log_entry['source'] == 'test'
        assert log_entry['context']['request_id'] == test_context['request_id']
        assert log_entry['context']['user_id'] == test_context['user_id']
        assert log_entry['metadata']['operation'] == test_metadata['operation']
        assert log_entry['metadata']['duration_ms'] == test_metadata['duration_ms']

    def test_context_logger(self):
        """Test that ContextLogger properly manages context."""
        outer_context = {'request_id': '123'}
        inner_context = {'user_id': '456'}
        
        with ContextLogger(self.test_logger, **outer_context):
            self.test_logger.info("Outer message")
            
            with ContextLogger(self.test_logger, **inner_context):
                self.test_logger.info("Inner message")
            
            self.test_logger.info("Outer message again")
        
        time.sleep(0.1)
        
        with open(os.path.join(self.test_log_dir, 'test.log'), 'r') as f:
            lines = f.readlines()
            logs = [json.loads(line) for line in lines[-3:]]
        
        # Verify context handling
        assert logs[0]['context']['request_id'] == '123'
        assert 'user_id' not in logs[0]['context']
        
        assert logs[1]['context']['request_id'] == '123'
        assert logs[1]['context']['user_id'] == '456'
        
        assert logs[2]['context']['request_id'] == '123'
        assert 'user_id' not in logs[2]['context']

    def test_log_sanitization(self):
        """Test that sensitive data is properly sanitized."""
        sensitive_data = {
            'email': 'test@example.com',
            'password': 'secret123',
            'credit_card': '4111-1111-1111-1111',
            'api_key': 'sk_test_123456789'
        }
        
        self.test_logger.info("Sensitive data test", extra={
            'metadata': sensitive_data
        })
        
        time.sleep(0.1)
        
        with open(os.path.join(self.test_log_dir, 'test.log'), 'r') as f:
            log_entry = json.loads(f.readlines()[-1])
        
        # Verify that sensitive data is redacted
        metadata = log_entry['metadata']
        assert metadata['email'] == '[REDACTED_EMAIL]'
        assert metadata['password'] == '[REDACTED_PASSWORD]'
        assert metadata['credit_card'] == '[REDACTED_CREDIT_CARD]'
        assert metadata['api_key'] == '[REDACTED_API_KEY]'

    def test_error_logging(self):
        """Test error logging with stack traces."""
        test_error = ValueError("Test error")
        
        try:
            raise test_error
        except Exception as e:
            self.test_logger.error("Error occurred", exc_info=True)
        
        time.sleep(0.1)
        
        with open(os.path.join(self.test_log_dir, 'test.log'), 'r') as f:
            log_entry = json.loads(f.readlines()[-1])
        
        # Verify error logging
        assert log_entry['level'] == 'ERROR'
        assert 'exc_info' in log_entry
        assert 'ValueError: Test error' in log_entry['exc_info'] 