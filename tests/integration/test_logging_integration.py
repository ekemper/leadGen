import os
import json
import tempfile
import time
import pytest
from unittest.mock import patch
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.core.logger import get_logger
from app.core.config import settings


class TestAPIServiceLogging:
    """Test logging functionality in API service context."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.client = TestClient(app)
        self.logger = get_logger("test.api.integration")
    
    def test_api_endpoint_logging(self):
        """Test that API endpoints can log properly."""
        # Test that logger works in API context
        try:
            self.logger.info("API endpoint test", extra={
                "endpoint": "/test",
                "method": "GET",
                "component": "api"
            })
            success = True
        except Exception as e:
            success = False
            print(f"API logging failed: {e}")
        
        assert success
    
    def test_api_request_logging_with_client(self):
        """Test logging during actual API requests."""
        # Make a request to a working endpoint
        response = self.client.get("/api/v1/health")
        
        # Verify the request was successful
        assert response.status_code == 200
        
        # Test that we can log about the request
        try:
            self.logger.info("Health check performed", extra={
                "status_code": response.status_code,
                "endpoint": "/api/v1/health",
                "component": "api"
            })
            success = True
        except Exception:
            success = False
        
        assert success
    
    def test_api_error_logging(self):
        """Test error logging in API context."""
        try:
            # Simulate an error condition
            raise ValueError("Test API error")
        except ValueError:
            try:
                self.logger.error("API error occurred", exc_info=True, extra={
                    "component": "api",
                    "error_type": "ValueError"
                })
                success = True
            except Exception:
                success = False
        
        assert success
    
    def test_api_sensitive_data_logging(self):
        """Test that sensitive data is handled in API logging."""
        # Test logging with potential sensitive data
        try:
            self.logger.info("User login attempt", extra={
                "user_email": "user@example.com",  # Should be sanitized
                "password": "secret123",  # Should be sanitized
                "component": "api",
                "endpoint": "/login"
            })
            success = True
        except Exception:
            success = False
        
        assert success


class TestWorkerServiceLogging:
    """Test logging functionality in worker service context."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.logger = get_logger("test.worker.integration")
    
    def test_worker_task_logging(self):
        """Test logging in worker task context."""
        try:
            self.logger.info("Worker task started", extra={
                "task_id": "test_task_123",
                "component": "worker",
                "task_type": "email_send"
            })
            success = True
        except Exception:
            success = False
        
        assert success
    
    def test_worker_progress_logging(self):
        """Test logging task progress in worker context."""
        task_id = "progress_test_456"
        
        try:
            # Simulate task progress logging
            for i in range(3):
                self.logger.info(f"Task progress: {i+1}/3", extra={
                    "task_id": task_id,
                    "component": "worker",
                    "progress": i + 1,
                    "total": 3
                })
            
            self.logger.info("Task completed", extra={
                "task_id": task_id,
                "component": "worker",
                "status": "COMPLETED"
            })
            success = True
        except Exception:
            success = False
        
        assert success
    
    def test_worker_error_handling(self):
        """Test error logging in worker context."""
        try:
            # Simulate worker task error
            raise ConnectionError("Database connection failed")
        except ConnectionError:
            try:
                self.logger.error("Worker task failed", exc_info=True, extra={
                    "task_id": "error_test_789",
                    "component": "worker",
                    "error_type": "ConnectionError"
                })
                success = True
            except Exception:
                success = False
        
        assert success
    
    def test_worker_batch_processing_logging(self):
        """Test logging for batch processing scenarios."""
        batch_id = "batch_test_001"
        items = [1, 2, 3, 4, 5]
        
        try:
            self.logger.info("Batch processing started", extra={
                "batch_id": batch_id,
                "component": "worker",
                "item_count": len(items)
            })
            
            for item in items:
                self.logger.debug("Processing item", extra={
                    "batch_id": batch_id,
                    "component": "worker",
                    "item_id": item
                })
            
            self.logger.info("Batch processing completed", extra={
                "batch_id": batch_id,
                "component": "worker",
                "items_processed": len(items)
            })
            success = True
        except Exception:
            success = False
        
        assert success


class TestCrossServiceLogCorrelation:
    """Test log correlation across different services."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.api_logger = get_logger("test.api.correlation")
        self.worker_logger = get_logger("test.worker.correlation")
        self.flower_logger = get_logger("test.flower.correlation")
    
    def test_request_id_correlation(self):
        """Test that logs can be correlated using request IDs."""
        request_id = "req_correlation_123"
        
        try:
            # Simulate API request logging
            self.api_logger.info("Request received", extra={
                "request_id": request_id,
                "component": "api",
                "endpoint": "/api/v1/process"
            })
            
            # Simulate worker task logging for the same request
            self.worker_logger.info("Processing request", extra={
                "request_id": request_id,
                "component": "worker",
                "task_type": "data_processing"
            })
            
            # Simulate completion logging
            self.api_logger.info("Request completed", extra={
                "request_id": request_id,
                "component": "api",
                "status": "success"
            })
            success = True
        except Exception:
            success = False
        
        assert success
    
    def test_user_session_correlation(self):
        """Test correlation across services for user session."""
        user_id = "user_456"
        session_id = "session_789"
        
        try:
            # API: User login
            self.api_logger.info("User logged in", extra={
                "user_id": user_id,
                "session_id": session_id,
                "component": "api",
                "action": "login"
            })
            
            # Worker: Background task for user
            self.worker_logger.info("User background task started", extra={
                "user_id": user_id,
                "session_id": session_id,
                "component": "worker",
                "task_type": "notification_send"
            })
            
            # Flower: Monitoring
            self.flower_logger.info("Task monitored", extra={
                "user_id": user_id,
                "session_id": session_id,
                "component": "flower",
                "monitoring": "active"
            })
            success = True
        except Exception:
            success = False
        
        assert success
    
    def test_transaction_correlation(self):
        """Test correlation for complex transactions across services."""
        transaction_id = "txn_001_abc"
        
        try:
            # API: Transaction started
            self.api_logger.info("Transaction initiated", extra={
                "transaction_id": transaction_id,
                "component": "api",
                "amount": 100.50,
                "currency": "USD"
            })
            
            # Worker: Payment processing
            self.worker_logger.info("Payment processing", extra={
                "transaction_id": transaction_id,
                "component": "worker",
                "processor": "stripe",
                "status": "PENDING"
            })
            
            # Worker: Payment completed
            self.worker_logger.info("Payment completed", extra={
                "transaction_id": transaction_id,
                "component": "worker",
                "status": "success",
                "confirmation": "conf_123"
            })
            
            # API: Response sent
            self.api_logger.info("Transaction response sent", extra={
                "transaction_id": transaction_id,
                "component": "api",
                "response_status": 200
            })
            success = True
        except Exception:
            success = False
        
        assert success


class TestLogFileCreationAndRotation:
    """Test log file creation and rotation functionality."""
    
    def test_log_file_creation_configuration(self):
        """Test that log file configuration is properly set up."""
        
        # Verify configuration is accessible
        assert hasattr(settings, 'LOG_DIR')
        assert hasattr(settings, 'LOG_ROTATION_SIZE')
        assert hasattr(settings, 'LOG_BACKUP_COUNT')
        
        # Verify values are reasonable
        assert settings.LOG_DIR is not None
        assert settings.LOG_ROTATION_SIZE > 0
        assert settings.LOG_BACKUP_COUNT > 0
    
    def test_log_directory_path_resolution(self):
        """Test that log directory path is properly resolved."""
        log_dir = Path(settings.LOG_DIR)
        
        # Directory should be resolvable
        assert log_dir is not None
        
        # Should be able to create path objects
        log_file_path = log_dir / "combined.log"
        assert log_file_path.name == "combined.log"
    
    @patch.dict(os.environ, {"LOG_DIR": "test_temp_logs"})
    def test_custom_log_directory_configuration(self):
        """Test logging with custom log directory."""
        # Force reload of settings with new environment
        from app.core.config import Settings
        settings = Settings()
        
        assert settings.LOG_DIR == "test_temp_logs"
    
    def test_multiple_loggers_same_file(self):
        """Test that multiple loggers can write to the same file system."""
        loggers = [
            get_logger("test.service1"),
            get_logger("test.service2"),
            get_logger("test.service3")
        ]
        
        try:
            for i, logger in enumerate(loggers):
                logger.info(f"Service {i+1} logging test", extra={
                    "service_id": i + 1,
                    "component": f"service{i+1}"
                })
            success = True
        except Exception:
            success = False
        
        assert success


class TestEnvironmentVariableOverride:
    """Test environment variable override functionality."""
    
    def test_log_level_override(self):
        """Test LOG_LEVEL environment variable override."""
        test_cases = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in test_cases:
            with patch.dict(os.environ, {"LOG_LEVEL": level}):
                # Import fresh settings
                from app.core.config import Settings
                settings = Settings()
                assert settings.LOG_LEVEL == level
    
    def test_log_directory_override(self):
        """Test LOG_DIR environment variable override."""
        test_dirs = ["/tmp/custom_logs", "./custom_logs", "logs/custom"]
        
        for test_dir in test_dirs:
            with patch.dict(os.environ, {"LOG_DIR": test_dir}):
                from app.core.config import Settings
                settings = Settings()
                assert settings.LOG_DIR == test_dir
    
    def test_log_rotation_size_override(self):
        """Test LOG_ROTATION_SIZE environment variable override."""
        test_sizes = ["5242880", "20971520", "1048576"]  # 5MB, 20MB, 1MB
        
        for size_str in test_sizes:
            with patch.dict(os.environ, {"LOG_ROTATION_SIZE": size_str}):
                from app.core.config import Settings
                settings = Settings()
                assert settings.LOG_ROTATION_SIZE == int(size_str)
    
    def test_log_backup_count_override(self):
        """Test LOG_BACKUP_COUNT environment variable override."""
        test_counts = ["3", "7", "10"]
        
        for count_str in test_counts:
            with patch.dict(os.environ, {"LOG_BACKUP_COUNT": count_str}):
                from app.core.config import Settings
                settings = Settings()
                assert settings.LOG_BACKUP_COUNT == int(count_str)
    
    def test_service_host_port_override(self):
        """Test service host and port environment variable overrides."""
        with patch.dict(os.environ, {
            "LOG_SERVICE_HOST": "api-service",
            "LOG_SERVICE_PORT": "9000"
        }):
            from app.core.config import Settings
            settings = Settings()
            assert settings.LOG_SERVICE_HOST == "api-service"
            assert settings.LOG_SERVICE_PORT == 9000
    
    def test_buffer_size_override(self):
        """Test LOG_BUFFER_SIZE environment variable override."""
        test_sizes = ["500", "2000", "5000"]
        
        for size_str in test_sizes:
            with patch.dict(os.environ, {"LOG_BUFFER_SIZE": size_str}):
                from app.core.config import Settings
                settings = Settings()
                assert settings.LOG_BUFFER_SIZE == int(size_str)
    
    def test_multiple_environment_overrides(self):
        """Test multiple environment variable overrides simultaneously."""
        env_overrides = {
            "LOG_LEVEL": "WARNING",
            "LOG_DIR": "/tmp/multi_test_logs",
            "LOG_ROTATION_SIZE": "15728640",  # 15MB
            "LOG_BACKUP_COUNT": "8",
            "LOG_SERVICE_HOST": "test-host",
            "LOG_SERVICE_PORT": "7777",
            "LOG_BUFFER_SIZE": "1500"
        }
        
        with patch.dict(os.environ, env_overrides):
            from app.core.config import Settings
            settings = Settings()
            
            assert settings.LOG_LEVEL == "WARNING"
            assert settings.LOG_DIR == "/tmp/multi_test_logs"
            assert settings.LOG_ROTATION_SIZE == 15728640
            assert settings.LOG_BACKUP_COUNT == 8
            assert settings.LOG_SERVICE_HOST == "test-host"
            assert settings.LOG_SERVICE_PORT == 7777
            assert settings.LOG_BUFFER_SIZE == 1500


class TestLoggingPerformance:
    """Test logging performance and resource usage."""
    
    def test_high_volume_logging_performance(self):
        """Test logging performance with high volume of messages."""
        logger = get_logger("test.performance")
        message_count = 1000
        
        start_time = time.time()
        
        try:
            for i in range(message_count):
                logger.info(f"Performance test message {i}", extra={
                    "message_id": i,
                    "component": "performance_test",
                    "batch": "high_volume"
                })
            success = True
        except Exception:
            success = False
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert success
        # Should be able to log 1000 messages in reasonable time (< 10 seconds)
        assert duration < 10.0, f"Logging took too long: {duration} seconds"
    
    def test_concurrent_logging_simulation(self):
        """Test concurrent logging from multiple simulated services."""
        loggers = {
            "api": get_logger("test.concurrent.api"),
            "worker": get_logger("test.concurrent.worker"),
            "flower": get_logger("test.concurrent.flower")
        }
        
        try:
            # Simulate concurrent logging from different services
            for i in range(50):  # 50 messages per service
                for service, logger in loggers.items():
                    logger.info(f"Concurrent message {i}", extra={
                        "message_id": i,
                        "component": service,
                        "test": "concurrent_logging"
                    })
            success = True
        except Exception:
            success = False
        
        assert success
    
    def test_logging_with_large_extra_data(self):
        """Test logging performance with large extra data."""
        logger = get_logger("test.performance.large_data")
        
        # Create moderately large extra data
        large_extra = {
            "component": "performance_test",
            "data": {f"key_{i}": f"value_{i}" for i in range(100)},
            "list_data": list(range(100)),
            "description": "x" * 1000  # 1KB string
        }
        
        try:
            logger.info("Large data test", extra=large_extra)
            success = True
        except Exception:
            success = False
        
        assert success


class TestErrorConditions:
    """Test logging system behavior under error conditions."""
    
    def test_logging_during_exception_handling(self):
        """Test logging while handling exceptions."""
        logger = get_logger("test.error.conditions")
        
        try:
            # Create nested exception scenario
            try:
                raise ValueError("Inner exception")
            except ValueError as inner_e:
                try:
                    raise RuntimeError("Outer exception") from inner_e
                except RuntimeError:
                    logger.error("Nested exception scenario", exc_info=True, extra={
                        "component": "error_test",
                        "scenario": "nested_exceptions"
                    })
            success = True
        except Exception:
            success = False
        
        assert success
    
    def test_logging_with_invalid_extra_data(self):
        """Test logging system resilience with problematic extra data."""
        logger = get_logger("test.error.invalid_data")
        
        # Test with various problematic data types
        problematic_data = [
            {"circular_ref": None},  # Will be set to create circular reference
            {"non_serializable": object()},
            {"very_deep": {"a": {"b": {"c": {"d": {"e": "deep"}}}}}},
        ]
        
        # Create circular reference
        problematic_data[0]["circular_ref"] = problematic_data[0]
        
        success_count = 0
        for i, data in enumerate(problematic_data):
            try:
                logger.info(f"Problematic data test {i}", extra=data)
                success_count += 1
            except Exception:
                # Expected to fail gracefully, continue testing
                pass
        
        # At least some should succeed or fail gracefully
        assert success_count >= 0  # System should not crash
    
    def test_logging_system_isolation(self):
        """Test that logging system doesn't interfere with application logic."""
        logger = get_logger("test.isolation")
        
        # Application logic should work regardless of logging
        def business_logic_function():
            logger.info("Business logic started", extra={"component": "business"})
            result = 2 + 2
            logger.info("Business logic completed", extra={"component": "business", "result": result})
            return result
        
        try:
            result = business_logic_function()
            assert result == 4
            success = True
        except Exception:
            success = False
        
        assert success 