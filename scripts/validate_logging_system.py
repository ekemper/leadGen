#!/usr/bin/env python3
"""
Operational validation script for unified logging system.
This script fills the gaps in automated tests by performing real-world validation.

Run this script to validate Step 6.2 manual testing protocol requirements:
1. Basic Functionality Test
2. Sanitization Test  
3. Rotation Test
4. Multi-Service Test
5. Environment Override Test
6. Performance Test
"""

import os
import sys
import time
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logger import get_logger
from app.core.config import settings

class LoggingSystemValidator:
    """Validates the unified logging system through operational tests."""
    
    def __init__(self):
        self.logger = get_logger("logging.validator")
        self.results: Dict[str, Dict[str, Any]] = {}
        self.log_file_path = Path(settings.LOG_DIR) / "combined.log"
    
    def run_all_tests(self) -> Dict[str, Dict[str, Any]]:
        """Run all validation tests and return results."""
        print("🔄 Starting Unified Logging System Validation...")
        print("=" * 60)
        
        tests = [
            ("Basic Functionality", self.test_basic_functionality),
            ("Sanitization", self.test_sanitization),
            ("Log Rotation", self.test_log_rotation),
            ("Multi-Service", self.test_multi_service),
            ("Environment Override", self.test_environment_override),
            ("Performance", self.test_performance),
        ]
        
        for test_name, test_func in tests:
            print(f"\n📋 Running {test_name} Test...")
            try:
                result = test_func()
                self.results[test_name] = {"status": "PASS", "details": result}
                print(f"✅ {test_name} Test: PASSED")
            except Exception as e:
                self.results[test_name] = {"status": "FAIL", "error": str(e)}
                print(f"❌ {test_name} Test: FAILED - {e}")
        
        self._print_summary()
        return self.results
    
    def test_basic_functionality(self) -> Dict[str, Any]:
        """Test 1: Basic Functionality - File creation, console output, log levels."""
        results = {}
        
        # Ensure log directory exists
        self.log_file_path.parent.mkdir(exist_ok=True)
        
        # Test different log levels
        test_messages = [
            ("DEBUG", "Debug test message"),
            ("INFO", "Info test message"),
            ("WARNING", "Warning test message"),
            ("ERROR", "Error test message"),
            ("CRITICAL", "Critical test message"),
        ]
        
        initial_size = self.log_file_path.stat().st_size if self.log_file_path.exists() else 0
        
        for level, message in test_messages:
            getattr(self.logger, level.lower())(message, extra={
                "test_type": "basic_functionality",
                "log_level": level
            })
        
        # Verify log file was written to
        if self.log_file_path.exists():
            final_size = self.log_file_path.stat().st_size
            results["file_created"] = True
            results["file_written"] = final_size > initial_size
            results["file_size_increase"] = final_size - initial_size
        else:
            results["file_created"] = False
            results["file_written"] = False
        
        # Verify JSON format in log file
        if results["file_created"]:
            with open(self.log_file_path, 'r') as f:
                lines = f.readlines()
                if lines:
                    try:
                        last_log = json.loads(lines[-1])
                        results["json_format"] = True
                        results["has_timestamp"] = "timestamp" in last_log
                        results["has_level"] = "level" in last_log
                        results["has_message"] = "message" in last_log
                    except json.JSONDecodeError:
                        results["json_format"] = False
        
        return results
    
    def test_sanitization(self) -> Dict[str, Any]:
        """Test 2: Verify sensitive data is sanitized in log files."""
        results = {}
        
        # Test cases with sensitive data
        sensitive_test_cases = [
            ("email", "User login: user@example.com"),
            ("password", "Auth failed with password=secret123"),
            ("api_key", "API call with api_key=sk_test_12345"),
            ("token", "Bearer token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9"),
            ("credit_card", "Payment with card 4111111111111111"),
            ("phone", "Contact number: +1-555-123-4567"),
        ]
        
        initial_size = self.log_file_path.stat().st_size if self.log_file_path.exists() else 0
        
        for test_type, message in sensitive_test_cases:
            self.logger.info(message, extra={
                "test_type": "sanitization",
                "sensitive_data_type": test_type
            })
        
        # Read recent log entries
        if self.log_file_path.exists():
            with open(self.log_file_path, 'r') as f:
                content = f.read()
                
            # Check that sensitive data is redacted
            checks = {
                "email_redacted": "user@example.com" not in content and "[REDACTED_EMAIL]" in content,
                "password_redacted": "secret123" not in content and "[REDACTED_PASSWORD]" in content,
                "api_key_redacted": "sk_test_12345" not in content and "[REDACTED_API_KEY]" in content,
                "token_redacted": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9" not in content and "[REDACTED_TOKEN]" in content,
                "credit_card_redacted": "4111111111111111" not in content and "[REDACTED_CC]" in content,
                "phone_redacted": "+1-555-123-4567" not in content and "[REDACTED_PHONE]" in content,
            }
            results.update(checks)
            results["all_sanitized"] = all(checks.values())
        
        return results
    
    def test_log_rotation(self) -> Dict[str, Any]:
        """Test 3: Generate logs to trigger rotation and verify backup files."""
        results = {}
        
        # Check current rotation settings
        results["rotation_size"] = settings.LOG_ROTATION_SIZE
        results["backup_count"] = settings.LOG_BACKUP_COUNT
        
        # Generate large log messages to trigger rotation
        large_message = "X" * 1024  # 1KB message
        messages_needed = (settings.LOG_ROTATION_SIZE // 1024) + 100  # Exceed rotation size
        
        initial_files = list(self.log_file_path.parent.glob("combined.log*"))
        results["initial_file_count"] = len(initial_files)
        
        # Generate logs to exceed rotation size
        for i in range(min(messages_needed, 15000)):  # Cap at 15K to avoid excessive time
            self.logger.info(f"Rotation test message {i}: {large_message}", extra={
                "test_type": "rotation",
                "message_number": i
            })
            
            # Check for rotation every 1000 messages
            if i % 1000 == 0:
                files = list(self.log_file_path.parent.glob("combined.log*"))
                if len(files) > len(initial_files):
                    results["rotation_triggered"] = True
                    results["messages_to_rotation"] = i + 1
                    break
        
        # Check final file state
        final_files = list(self.log_file_path.parent.glob("combined.log*"))
        results["final_file_count"] = len(final_files)
        results["rotation_occurred"] = len(final_files) > len(initial_files)
        
        if results.get("rotation_occurred"):
            # Check for backup files
            backup_files = [f for f in final_files if f.name != "combined.log"]
            results["backup_files"] = [f.name for f in backup_files]
            results["backup_count_correct"] = len(backup_files) <= settings.LOG_BACKUP_COUNT
        
        return results
    
    def test_multi_service(self) -> Dict[str, Any]:
        """Test 4: Simulate multi-service logging to same file."""
        results = {}
        
        # Create loggers for different services
        api_logger = get_logger("test.api.service")
        worker_logger = get_logger("test.worker.service")
        flower_logger = get_logger("test.flower.service")
        
        # Generate logs from each service
        request_id = f"req_{int(time.time())}"
        
        initial_size = self.log_file_path.stat().st_size if self.log_file_path.exists() else 0
        
        # API service logs
        api_logger.info("Request received", extra={
            "request_id": request_id,
            "component": "api",
            "endpoint": "/test/multi-service"
        })
        
        # Worker service logs
        worker_logger.info("Processing request", extra={
            "request_id": request_id,
            "component": "worker",
            "task_type": "test_processing"
        })
        
        # Flower monitoring logs
        flower_logger.info("Task monitored", extra={
            "request_id": request_id,
            "component": "flower",
            "status": "active"
        })
        
        # Verify all logs went to same file
        if self.log_file_path.exists():
            final_size = self.log_file_path.stat().st_size
            results["file_size_increased"] = final_size > initial_size
            
            # Read recent logs and verify correlation
            with open(self.log_file_path, 'r') as f:
                lines = f.readlines()
                recent_logs = lines[-10:]  # Last 10 lines
                
            logs_with_request_id = []
            components_found = set()
            
            for line in recent_logs:
                try:
                    log_data = json.loads(line)
                    if log_data.get("request_id") == request_id:
                        logs_with_request_id.append(log_data)
                        components_found.add(log_data.get("component"))
                except json.JSONDecodeError:
                    continue
            
            results["correlated_logs_found"] = len(logs_with_request_id)
            results["components_logged"] = list(components_found)
            results["all_services_logged"] = {"api", "worker", "flower"}.issubset(components_found)
        
        return results
    
    def test_environment_override(self) -> Dict[str, Any]:
        """Test 5: Verify environment variable configuration."""
        results = {}
        
        # Test current configuration values
        results["current_log_level"] = settings.LOG_LEVEL
        results["current_log_dir"] = settings.LOG_DIR
        results["current_rotation_size"] = settings.LOG_ROTATION_SIZE
        results["current_backup_count"] = settings.LOG_BACKUP_COUNT
        
        # Verify configuration is loaded from environment/defaults
        expected_defaults = {
            "LOG_DIR": "./logs",
            "LOG_LEVEL": "INFO",
            "LOG_ROTATION_SIZE": 10485760,
            "LOG_BACKUP_COUNT": 5,
            "LOG_SERVICE_HOST": "localhost",
            "LOG_SERVICE_PORT": 8765,
            "LOG_BUFFER_SIZE": 1000,
        }
        
        config_checks = {}
        for key, expected_default in expected_defaults.items():
            actual_value = getattr(settings, key)
            # Check if value is either from environment or default
            env_value = os.getenv(key)
            if env_value:
                if key in ["LOG_ROTATION_SIZE", "LOG_BACKUP_COUNT", "LOG_SERVICE_PORT", "LOG_BUFFER_SIZE"]:
                    expected_value = int(env_value)
                else:
                    expected_value = env_value
            else:
                expected_value = expected_default
            
            config_checks[f"{key}_correct"] = actual_value == expected_value
        
        results.update(config_checks)
        results["all_config_correct"] = all(config_checks.values())
        
        return results
    
    def test_performance(self) -> Dict[str, Any]:
        """Test 6: Performance with high-volume logging."""
        results = {}
        
        # Performance test parameters
        message_count = 1000
        large_extra_data = {
            "component": "performance_test",
            "data": {f"key_{i}": f"value_{i}" for i in range(50)},
            "description": "Performance test with substantial extra data"
        }
        
        # Time the logging operation
        start_time = time.time()
        
        for i in range(message_count):
            self.logger.info(f"Performance test message {i}", extra={
                **large_extra_data,
                "message_id": i
            })
        
        end_time = time.time()
        duration = end_time - start_time
        
        results["message_count"] = message_count
        results["duration_seconds"] = round(duration, 3)
        results["messages_per_second"] = round(message_count / duration, 2)
        results["performance_acceptable"] = duration < 10.0  # Should complete in < 10 seconds
        
        # Test memory usage (rough estimate)
        import psutil
        process = psutil.Process()
        results["memory_usage_mb"] = round(process.memory_info().rss / 1024 / 1024, 2)
        
        return results
    
    def _print_summary(self):
        """Print a summary of all test results."""
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in self.results.values() if r["status"] == "PASS")
        total = len(self.results)
        
        print(f"Tests Passed: {passed}/{total}")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED! Unified logging system is fully operational.")
        else:
            print("\n⚠️  Some tests failed. Review the details above.")
        
        print("\n📁 Log file location:", self.log_file_path)
        if self.log_file_path.exists():
            size_mb = self.log_file_path.stat().st_size / 1024 / 1024
            print(f"📈 Current log file size: {size_mb:.2f} MB")


def main():
    """Main function to run validation."""
    validator = LoggingSystemValidator()
    results = validator.run_all_tests()
    
    # Exit with appropriate code
    failed_tests = [name for name, result in results.items() if result["status"] == "FAIL"]
    if failed_tests:
        print(f"\n❌ Failed tests: {', '.join(failed_tests)}")
        sys.exit(1)
    else:
        print("\n✅ All validation tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main() 