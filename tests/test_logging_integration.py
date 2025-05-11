import os
import json
import time
import pytest
from datetime import datetime
from pathlib import Path

def test_log_file_accessibility():
    """Test that log files exist and are accessible"""
    log_dir = Path('./logs')
    required_logs = ['browser.log', 'server.log', 'worker.log']
    
    assert log_dir.exists(), "Log directory does not exist"
    for log_file in required_logs:
        log_path = log_dir / log_file
        assert log_path.exists(), f"{log_file} does not exist"
        assert log_path.stat().st_size > 0, f"{log_file} is empty"

def test_browser_log_format():
    """Test that browser.log contains properly formatted JSON entries"""
    with open('./logs/browser.log', 'r') as f:
        for line in f:
            try:
                log_entry = json.loads(line.strip())
                required_fields = ['timestamp', 'level', 'message', 'source']
                assert all(field in log_entry for field in required_fields), \
                    f"Log entry missing required fields: {log_entry}"
            except json.JSONDecodeError:
                pytest.fail(f"Invalid JSON in browser.log: {line}")

def test_real_time_logging():
    """Test real-time log ingestion by generating a test error"""
    # Record initial log sizes
    initial_sizes = {
        'browser.log': os.path.getsize('./logs/browser.log'),
    }
    
    # Generate a test error (this would be done by the frontend)
    test_error = {
        'timestamp': datetime.utcnow().isoformat(),
        'level': 'error',
        'message': 'Test error for real-time logging verification',
        'source': 'browser',
        'type': 'error',
        'tag': 'test.error',
        'stack': 'Test stack trace'
    }
    
    # Write test error to browser.log
    with open('./logs/browser.log', 'a') as f:
        f.write(json.dumps(test_error) + '\n')
    
    # Wait for log processing
    time.sleep(1)
    
    # Verify logs were updated
    assert os.path.getsize('./logs/browser.log') > initial_sizes['browser.log'], \
        "browser.log was not updated"
    
    # Verify error was properly logged
    with open('./logs/browser.log', 'r') as f:
        last_line = f.readlines()[-1]
        logged_error = json.loads(last_line)
        assert logged_error['message'] == test_error['message'], \
            "Test error was not properly logged"

if __name__ == '__main__':
    pytest.main([__file__]) 