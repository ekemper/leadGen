# Unified Logging System Migration Plan

## Executive Summary

This plan implements a unified logging system for the FastAPI K8s prototype application. The system will provide consistent logging patterns across all containers with proper sanitization, structured JSON output, and centralized log management.

**Current State Assessment:**
- ✅ Advanced logging configuration already exists in `app/core/logging_config.py`
- ✅ JSON formatting with sanitization is implemented
- ❌ Missing logger utility helper (`logger.py`)
- ❌ Missing Docker volume mapping for logs
- ❌ Missing environment variable configuration
- ❌ Missing comprehensive documentation
- ❌ Missing test suite

## Step-by-Step Implementation Plan

### Phase 1: Environment Configuration & Dependencies

#### Step 1.1: Update Environment Variables
**Action:** Add logging environment variables to the configuration system.

**Files to modify:**
- `app/core/config.py`
- `.env` (create/update)

**Implementation:**
1. Add logging configuration to `Settings` class in `app/core/config.py`:
```python
# Logging Configuration
LOG_DIR: str = "./logs"
LOG_LEVEL: str = "INFO"
LOG_ROTATION_SIZE: int = 10485760  # 10MB
LOG_BACKUP_COUNT: int = 5
LOG_SERVICE_HOST: str = "localhost"
LOG_SERVICE_PORT: int = 8765
LOG_BUFFER_SIZE: int = 1000
```

2. Create/update `.env` file with logging variables:
```env
LOG_DIR=./logs
LOG_LEVEL=INFO
LOG_ROTATION_SIZE=10485760
LOG_BACKUP_COUNT=5
LOG_SERVICE_HOST=localhost
LOG_SERVICE_PORT=8765
LOG_BUFFER_SIZE=1000
```

**Note:** The existing `Settings` class in `config.py` already uses `pydantic-settings` with `env_file = ".env"` configuration, which means it automatically reads environment variables from the `.env` file. The logging configuration will be seamlessly integrated with this existing pattern.

#### Step 1.2: Update Dependencies
**Action:** Add required logging dependencies to requirements files.

**Files to modify:**
- `requirements/base.txt`

**Implementation:**
Add to `requirements/base.txt`:
```
python-json-logger==2.0.7
colorama==0.4.6
```

**Installation Instructions:**
After adding the dependencies to `requirements/base.txt`, install them using the appropriate requirements file for your environment:

For development:
```bash
pip install -r requirements/dev.txt
```

For production:
```bash
pip install -r requirements/prod.txt
```

For base only:
```bash
pip install -r requirements/base.txt
```

**Note:** The project uses a structured requirements approach where `dev.txt` and `prod.txt` include `base.txt` via the `-r base.txt` directive, ensuring consistent core dependencies across environments.

#### Step 1.3: Update Logging Configuration
**Action:** Enhance existing logging configuration to use environment variables.

**Files to modify:**
- `app/core/logging_config.py`

**Implementation:**
1. Import settings from config
2. Replace hardcoded values with environment variables from settings
3. Update LOG_DIR to use settings.LOG_DIR
4. Update MAX_BYTES to use settings.LOG_ROTATION_SIZE
5. Update BACKUP_COUNT to use settings.LOG_BACKUP_COUNT

### Phase 2: Create Logger Utility

#### Step 2.1: Create Logger Helper
**Action:** Create the logger utility as specified in requirements.

**Files to create:**
- `app/core/logger.py`

**Implementation:**
```python
from __future__ import annotations
import logging
from typing import Optional

# Ensure central logging is initialised once this module is imported
from app.core.logging_config import init_logging  # noqa: F401


def get_logger(name: Optional[str] = None) -> logging.Logger:  # pragma: no cover
    """Return a logger that is guaranteed to be configured.

    If *name* is omitted, the root "app" logger is returned.  This helper exists so
    that modules can simply do::

        from app.core.logger import get_logger
        logger = get_logger(__name__)
    """
    if name is None:
        name = "app"
    return logging.getLogger(name) 
```

### Phase 3: Docker Configuration

#### Step 3.1: Update Docker Compose Files
**Action:** Add log volume mapping to all Docker Compose configurations.

**Files to modify:**
- `docker/docker-compose.yml`
- `docker/docker-compose.prod.yml`
- `docker/docker-compose.test.yml`

**Implementation:**
For each service (`api`, `worker`, `flower`), add volume mapping:
```yaml
volumes:
  - ./logs:/app/logs
  - # ... existing volumes
```

And add to the volumes section at the bottom:
```yaml
volumes:
  logs:
    driver: local
```

#### Step 3.2: Create Logs Directory
**Action:** Ensure logs directory exists and is properly configured.

**Implementation:**
1. Create `logs/` directory in project root
2. Add `.gitkeep` file to logs directory
3. Add `logs/*.log` to `.gitignore`

### Phase 4: Documentation

#### Step 4.1: Create Comprehensive Logging Documentation
**Action:** Create detailed documentation for the logging system.

**Files to create:**
- `documentation/LOGGING.md`

**Implementation:**
Create comprehensive documentation covering:
- System overview and architecture
- Configuration options
- Usage examples
- Log levels and when to use them
- Sensitive data handling
- Troubleshooting guide
- Performance considerations

### Phase 5: Testing

#### Step 5.1: Create Logging Test Suite
**Action:** Create comprehensive tests for the logging system.

**Files to create:**
- `tests/test_logging.py`

**Implementation:**
Create test suite covering:
1. Logger initialization
2. Log level configuration
3. Sensitive data sanitization
4. File rotation functionality
5. JSON formatting validation

#### Step 5.2: Integration Tests
**Action:** Create integration tests to verify logging across services.

**Files to create:**
- `tests/integration/test_logging_integration.py`

**Implementation:**
Test scenarios:
1. API service logging
2. Worker service logging
3. Cross-service log correlation
4. Log file creation and rotation
5. Environment variable override testing

### Phase 6: Migration and Validation

#### Step 6.1: Update Existing Code
**Action:** Update existing services to use the new logger utility.

**Files to scan and update:**
- All Python files in `app/` directory
- Replace direct logging imports with logger utility

**Implementation pattern:**
Replace:
```python
import logging
logger = logging.getLogger(__name__)
```

With:
```python
from app.core.logger import get_logger
logger = get_logger(__name__)
```

#### Step 6.2: Manual Testing Protocol
**Action:** Execute manual testing steps to validate the system.

**Testing Steps:**
1. **Basic Functionality Test:**
   - Start all services with Docker Compose
   - Verify `logs/combined.log` file is created
   - Generate test log messages at different levels
   - Confirm logs appear in both file and console

2. **Sanitization Test:**
   - Log messages containing sensitive data (emails, passwords, API keys)
   - Verify sensitive data is properly redacted in log files
   - Check both structured and string log messages

3. **Rotation Test:**
   - Generate logs exceeding LOG_ROTATION_SIZE
   - Verify log rotation creates backup files
   - Confirm old logs are properly archived

4. **Multi-Service Test:**
   - Generate logs from API, Worker, and background services
   - Verify all logs appear in the same combined.log file
   - Test log correlation across services

5. **Environment Override Test:**
   - Change LOG_LEVEL environment variable
   - Restart services
   - Verify new log level is applied

6. **Performance Test:**
   - Generate high-volume log messages
   - Monitor system performance
   - Verify log buffer and rotation performance

## Success Criteria

### Functional Requirements ✓
- [ ] Single unified logging system used throughout the application
- [ ] All services write to shared log file via Docker volume mapping
- [ ] Sensitive data automatically sanitized in all log output
- [ ] Environment variable configuration working correctly
- [ ] Log rotation functioning with configurable size and backup count
- [ ] JSON structured logging with proper timestamp and metadata

### Technical Requirements ✓
- [ ] Logger utility (`app/core/logger.py`) created and functional
- [ ] Docker volume mapping configured for all services
- [ ] Environment variables properly integrated with configuration system
- [ ] Existing logging configuration enhanced with environment variable support
- [ ] All Python dependencies added to requirements files

### Quality Requirements ✓
- [ ] Comprehensive test suite with >90% coverage
- [ ] Complete documentation in `documentation/LOGGING.md`
- [ ] Integration tests passing for all service types
- [ ] Manual testing protocol executed successfully
- [ ] No performance degradation in log-heavy operations

### Operational Requirements ✓
- [ ] Logs easily accessible via single file (`logs/combined.log`)
- [ ] Log files properly rotated to prevent disk space issues
- [ ] Clear error messages for configuration problems
- [ ] Easy log tailing and monitoring for developers
- [ ] AI agent can easily access logs for debugging context

## Risk Mitigation

### Potential Issues and Solutions:

1. **Log Volume Performance:**
   - Risk: High log volume impacting performance
   - Mitigation: Configurable buffer size and async logging

2. **Disk Space:**
   - Risk: Logs consuming excessive disk space
   - Mitigation: Configurable rotation size and backup count

3. **Sensitive Data Leakage:**
   - Risk: PII or secrets accidentally logged
   - Mitigation: Comprehensive sanitization patterns and testing

4. **Docker Volume Issues:**
   - Risk: Log files not persisting between container restarts
   - Mitigation: Proper Docker volume configuration and testing

5. **Migration Breaking Changes:**
   - Risk: Existing code broken during logger migration
   - Mitigation: Backward compatibility and gradual migration

## Implementation Timeline

- **Phase 1-2:** 2-3 hours (Configuration and logger utility)
- **Phase 3:** 1 hour (Docker configuration)
- **Phase 4:** 2-3 hours (Documentation)
- **Phase 5:** 3-4 hours (Testing)
- **Phase 6:** 2-3 hours (Migration and validation)

**Total Estimated Time:** 10-14 hours

## Dependencies and Prerequisites

- Python 3.9+ environment
- Docker and Docker Compose
- Existing FastAPI application structure
- PostgreSQL and Redis services
- Write access to project directory

## Post-Implementation Monitoring

1. Monitor log file sizes and rotation frequency
2. Validate log aggregation and search capabilities
3. Review sensitive data sanitization effectiveness
4. Monitor system performance impact
5. Gather developer feedback on usability

This plan provides a comprehensive approach to implementing the unified logging system while maintaining backward compatibility and ensuring robust testing and documentation. 