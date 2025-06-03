# FastAPI K8s Prototype - Unified Logging System

This document describes the unified logging system implemented for the FastAPI K8s prototype application. The system provides consistent logging patterns across all containers with proper sanitization, structured JSON output, and centralized log management.

## System Overview and Architecture

### Core Components

- **Central Configuration**: `app/core/logging_config.py` - Advanced logging configuration with JSON formatting and enhanced sanitization
- **Logger Utility**: `app/core/logger.py` - Convenience helper that guarantees proper logging initialization
- **Shared Log Directory**: `logs/` - Docker volume-mounted directory accessible by all services
- **Environment Configuration**: Environment variables integrated with `app/core/config.py` Settings class

### Services Integration

All containerized services use the unified logging system:
- **API Service** (`api`): FastAPI application logs
- **Worker Service** (`worker`): Celery worker logs with lifecycle tracking
- **Flower Service** (`flower`): Celery monitoring logs
- **Background Services**: Email verification, Apollo, OpenAI, Perplexity, and Instantly API services

### Worker Logging Integration

**Important**: As of the latest update, Celery workers are fully integrated with the centralized logging system. The `app/workers/celery_app.py` file includes:

- **Automatic Logging Initialization**: Workers initialize the centralized logging system on startup
- **Celery Signal Integration**: Worker lifecycle events (startup, shutdown, task execution) are logged
- **Task Execution Tracking**: All task starts, completions, and failures are logged with correlation IDs
- **Centralized Output**: All worker logs now appear in `logs/combined.log` alongside API logs

### Log Flow Architecture

```
Application Code → Logger Utility → Sanitization Filter → JSON Formatter → Multiple Outputs
     ↓                    ↓               ↓                    ↓              ↓
get_logger(__name__) → LogSanitizer → CustomJSONFormatter → File + Console
                            ↓                ↓                   ↓
                     Pattern Matching → Structured JSON → logs/combined.log
```

## Configuration Options

### Environment Variables

All logging configuration is controlled via environment variables in `.env`, automatically loaded by the Settings class:

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_DIR` | `./logs` | Directory for log files |
| `LOG_LEVEL` | `INFO` | Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `LOG_ROTATION_SIZE` | `10485760` | Log file size before rotation (10MB) |
| `LOG_BACKUP_COUNT` | `5` | Number of backup log files to keep |
| `LOG_SERVICE_HOST` | `localhost` | Service host for log correlation |
| `LOG_SERVICE_PORT` | `8765` | Service port for log correlation |
| `LOG_BUFFER_SIZE` | `1000` | Log buffer size for performance |

### Configuration in `app/core/config.py`

```python
class Settings(BaseSettings):
    # Logging Configuration
    LOG_DIR: str = "./logs"
    LOG_LEVEL: str = "INFO"
    LOG_ROTATION_SIZE: int = 10485760  # 10MB
    LOG_BACKUP_COUNT: int = 5
    LOG_SERVICE_HOST: str = "localhost"
    LOG_SERVICE_PORT: int = 8765
    LOG_BUFFER_SIZE: int = 1000

    @field_validator("LOG_ROTATION_SIZE", "LOG_BACKUP_COUNT", "LOG_SERVICE_PORT", "LOG_BUFFER_SIZE", mode="before")
    def validate_integers(cls, v):
        if isinstance(v, str):
            # Handle comments in env values (e.g., "10485760  # 10MB")
            value = v.split('#')[0].strip()
            return int(value)
        return v

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "allow"

settings = Settings()
```

## Usage Examples

### Basic Logger Usage

```python
from app.core.logger import get_logger

logger = get_logger(__name__)

# Basic logging
logger.info("User authentication successful")
logger.warning("Rate limit approaching")
logger.error("Database connection failed")
```

### Structured Logging with Context

```python
# Add context information
logger.info("User logged in", extra={
    "user_id": "12345",
    "component": "auth_service",
    "action": "login"
})

# Error logging with exception info
try:
    # some operation
    pass
except Exception as e:
    logger.error("Operation failed", exc_info=True, extra={
        "component": "payment_service",
        "operation": "process_payment"
    })
```

### Service-Specific Logging Patterns

```python
# API endpoint logging
logger = get_logger("app.api.endpoints.users")
logger.info("GET /users endpoint called", extra={
    "endpoint": "/users",
    "method": "GET",
    "component": "api"
})

# Worker task logging
logger = get_logger("app.workers.email_tasks")
logger.info("Email task started", extra={
    "task_id": "email_123",
    "component": "worker"
})

# Background service logging
logger = get_logger("app.background_services.apollo_service")
logger.info("Apollo API request completed", extra={
    "component": "apollo_service", 
    "records_processed": 150,
    "api_credits_used": 45
})
```

### Correlation Logging Across Services

```python
# Generate a correlation ID for tracking requests across services
import uuid
correlation_id = str(uuid.uuid4())

# API Service
api_logger = get_logger("app.api.campaigns")
api_logger.info("Campaign creation request", extra={
    "correlation_id": correlation_id,
    "component": "api",
    "endpoint": "/campaigns"
})

# Worker Service  
worker_logger = get_logger("app.workers.campaign_tasks")
worker_logger.info("Processing campaign creation", extra={
    "correlation_id": correlation_id,
    "component": "worker",
    "task_type": "create_campaign"
})

# Background Service
apollo_logger = get_logger("app.background_services.apollo_service")
apollo_logger.info("Enriching campaign leads", extra={
    "correlation_id": correlation_id,
    "component": "apollo_service",
    "leads_count": 100
})
```

## Log Levels and When to Use Them

### DEBUG
- **Use for**: Detailed diagnostic information
- **Examples**: Variable values, function entry/exit, detailed flow tracing
- **Note**: Only visible when LOG_LEVEL=DEBUG

```python
logger.debug("Processing user data", extra={"user_count": len(users)})
logger.debug("Apollo API response", extra={"response_size": len(response_data)})
```

### INFO
- **Use for**: General information about application flow
- **Examples**: Successful operations, key business events, service start/stop

```python
logger.info("User registration completed", extra={"user_id": user.id})
logger.info("Campaign created successfully", extra={"campaign_id": campaign.id})
```

### WARNING
- **Use for**: Recoverable errors or concerning situations
- **Examples**: Deprecated API usage, fallback mechanisms triggered, high resource usage

```python
logger.warning("Database connection slow", extra={"response_time": 5.2})
logger.warning("API rate limit approaching", extra={"requests_remaining": 10})
```

### ERROR
- **Use for**: Error conditions that don't stop the application
- **Examples**: Failed external API calls, data validation errors, recoverable exceptions

```python
logger.error("Payment processing failed", extra={"payment_id": payment.id})
logger.error("Apollo API request failed", extra={"status_code": 429, "retry_after": 60})
```

### CRITICAL
- **Use for**: Serious errors that may cause application failure
- **Examples**: Database unavailable, critical service failures, security breaches

```python
logger.critical("Database connection lost", extra={"service": "api"})
logger.critical("Authentication service unavailable", extra={"component": "auth"})
```

## Enhanced Sensitive Data Handling

### Automatic Sanitization with LogSanitizer

The logging system uses an advanced `LogSanitizer` class with comprehensive pattern matching:

**Sensitive Patterns Automatically Detected:**
- **Email addresses**: `user@example.com` → `[REDACTED_EMAIL]`
- **Passwords**: `password=secret123` → `password=[REDACTED_PASSWORD]`
- **API keys**: `api_key=sk_test_abc123` → `api_key=[REDACTED_API_KEY]`
- **Tokens**: `token=bearer_xyz789` → `token=[REDACTED_TOKEN]`
- **JWT tokens**: `eyJ0eXAiOiJKV1Q...` → `[REDACTED_TOKEN]`
- **Credit card numbers**: `4111111111111111` → `[REDACTED_CC]`
- **Phone numbers**: `+1-555-123-4567` → `[REDACTED_PHONE]`
- **UUIDs**: `550e8400-e29b-41d4-a716-446655440000` → `[REDACTED_UUID]`

### Enhanced Sanitization Features

```python
# The LogSanitizer handles complex nested data structures
class LogSanitizer:
    def sanitize_value(self, value: Any) -> Any:
        """Recursively sanitize values including nested dicts and lists."""
        if isinstance(value, dict):
            return {k: self.sanitize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.sanitize_value(item) for item in value]
        elif isinstance(value, str):
            return self.sanitize_string(value)
        return value
```

### Best Practices for Sensitive Data

```python
# GOOD: Log processing results without sensitive details
logger.info("Email verification completed", extra={
    "emails_processed": 100,
    "success_rate": 0.95,
    "component": "email_verifier"
})

# GOOD: Trust the sanitization for complex data
user_data = {"email": "user@example.com", "password": "secret123"}
logger.info("User data processed", extra={"user_data": user_data})  # Auto-sanitized

# GOOD: Log with safe identifiers
logger.info("Payment processed", extra={
    "payment_id": payment.id,
    "amount_cents": payment.amount_cents,
    "status": "completed"
    # Card details automatically sanitized if present
})
```

### Manual Data Sanitization

For extra security in critical scenarios:

```python
def safe_log_api_response(response_data):
    """Manually sanitize API response before logging."""
    safe_data = {
        "status_code": response_data.get("status"),
        "record_count": len(response_data.get("records", [])),
        "processing_time": response_data.get("processing_time")
        # Exclude any potentially sensitive response data
    }
    logger.info("API response processed", extra=safe_data)
```

## Log Output Format

### Enhanced JSON Structure

All logs are output as structured JSON with consistent fields and enhanced metadata:

```json
{
  "timestamp": "2025-01-20T10:30:45.123456Z",
  "level": "INFO",
  "name": "app.background_services.apollo_service",
  "message": "Lead enrichment completed",
  "source": "app.background_services.apollo_service",
  "component": "apollo_service",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "leads_processed": 150,
  "api_credits_used": 45,
  "processing_duration": 2.34,
  "service_host": "localhost",
  "service_port": 8765
}
```

### Mandatory Fields

| Field | Description | Example |
|-------|-------------|---------|
| `timestamp` | ISO-8601 UTC timestamp with microseconds | `2025-01-20T10:30:45.123456Z` |
| `level` | Log level | `INFO`, `ERROR`, `DEBUG` |
| `name` | Logger name (typically module path) | `app.background_services.apollo_service` |
| `message` | Human-readable message | `Lead enrichment completed` |
| `source` | Source identifier | Same as `name` unless overridden |

### Enhanced Optional Fields

| Field | Description | Example |
|-------|-------------|---------|
| `component` | Service/subsystem identifier | `apollo_service`, `worker`, `email_verifier` |
| `correlation_id` | Request/transaction correlation ID | `550e8400-e29b-41d4-a716-446655440000` |
| `service_host` | Service host from settings | `localhost`, `api-service` |
| `service_port` | Service port from settings | `8000`, `5555` |
| `user_id` | User context | `12345` |
| `campaign_id` | Campaign context | `camp_abc123` |
| `task_id` | Background task identifier | `email_verify_456` |
| `api_credits_used` | External API usage tracking | `45` |
| `processing_duration` | Operation timing | `2.34` |
| `error_code` | Application-specific error codes | `APOLLO_RATE_LIMIT` |

## Viewing and Monitoring Logs

### Local Development

**View live logs from all services:**
```bash
docker-compose -f docker/docker-compose.yml logs -f
```

**View specific service logs:**
```bash
docker-compose -f docker/docker-compose.yml logs -f api
docker-compose -f docker/docker-compose.yml logs -f worker
docker-compose -f docker/docker-compose.yml logs -f flower
```

**Monitor the unified log file:**
```bash
tail -f logs/combined.log | jq .
```

### Enhanced Log File Filtering

The structured JSON format enables powerful filtering and analysis:

**Filter by component:**
```bash
# API logs only
tail -f logs/combined.log | jq 'select(.component == "api")'

# Background service logs
tail -f logs/combined.log | jq 'select(.component | test("_service$"))'

# Worker task logs
tail -f logs/combined.log | jq 'select(.component == "worker")'
```

**Filter by correlation ID:**
```bash
# Follow a specific request across all services
tail -f logs/combined.log | jq 'select(.correlation_id == "550e8400-e29b-41d4-a716-446655440000")'
```

**Filter by log level and time:**
```bash
# Errors in the last hour
tail -f logs/combined.log | jq 'select(.level == "ERROR" and .timestamp > "'$(date -d '1 hour ago' -Iseconds)'")'

# Performance tracking
tail -f logs/combined.log | jq 'select(.processing_duration > 5.0)'
```

**Complex filtering for debugging:**
```bash
# Campaign-related errors with processing times
tail -f logs/combined.log | jq 'select(.campaign_id and (.level == "ERROR" or .processing_duration > 10.0))'

# API credit usage monitoring
tail -f logs/combined.log | jq 'select(.api_credits_used) | {timestamp, component, api_credits_used, correlation_id}'
```

### Log File Locations

- **Unified log file**: `logs/combined.log`
- **Rotated files**: `logs/combined.log.1`, `logs/combined.log.2`, etc.
- **Maximum retention**: Based on `LOG_BACKUP_COUNT` setting (default: 5 files)

## Troubleshooting Guide

### Common Issues

#### 1. No Log Files Created
**Symptoms**: `logs/combined.log` doesn't exist after starting services

**Solutions**:
- Check Docker volume mounting: `docker-compose -f docker/docker-compose.yml config`
- Verify logs directory exists: `ls -la logs/`
- Check container permissions: `docker exec <container> ls -la /app/logs/`
- Verify LOG_DIR setting: `echo $LOG_DIR` or check `.env` file

#### 2. Logs Not Appearing in File
**Symptoms**: Console logs work but file logs missing

**Solutions**:
- Check LOG_DIR environment variable in `.env`
- Verify write permissions in logs directory: `chmod 755 logs/`
- Check log level configuration (file might have different level)
- Verify logging initialization: Look for "Logging initialized" messages

#### 3. Sensitive Data Not Redacted
**Symptoms**: Passwords or emails appearing in logs

**Solutions**:
- Verify LogSanitizer patterns in `logging_config.py`
- Test sanitization with known patterns:
  ```python
  from app.core.logger import get_logger
  logger = get_logger("test")
  logger.info("Test email: user@example.com password=secret123")
  ```
- Check that SanitizingFilter is properly applied to all handlers

#### 4. Performance Issues with High Log Volume
**Symptoms**: Application slowdown during heavy logging

**Solutions**:
- Increase LOG_BUFFER_SIZE in `.env`: `LOG_BUFFER_SIZE=2000`
- Reduce LOG_LEVEL: `LOG_LEVEL=WARNING`
- Increase LOG_ROTATION_SIZE: `LOG_ROTATION_SIZE=52428800` (50MB)
- Monitor disk space: `df -h logs/`

#### 5. Docker Volume Issues
**Symptoms**: Logs not persisting between container restarts

**Solutions**:
```bash
# Check volume mounting in docker-compose.yml
grep -A 5 "volumes:" docker/docker-compose.yml

# Recreate volumes if needed
docker-compose -f docker/docker-compose.yml down -v
docker-compose -f docker/docker-compose.yml up -d

# Verify volume mapping
docker inspect $(docker-compose -f docker/docker-compose.yml ps -q api) | jq '.[].Mounts'
```

#### 6. Configuration Not Applied
**Symptoms**: Environment variable changes not taking effect

**Solutions**:
- Restart containers after `.env` changes
- Verify environment variable loading:
  ```python
  from app.core.config import settings
  print(f"Current LOG_LEVEL: {settings.LOG_LEVEL}")
  ```
- Check for typos in environment variable names
- Ensure `.env` file is in the correct location

### Enhanced Debugging Steps

1. **Check Current Configuration**:
   ```python
   from app.core.config import settings
   print(f"LOG_DIR: {settings.LOG_DIR}")
   print(f"LOG_LEVEL: {settings.LOG_LEVEL}")
   print(f"LOG_ROTATION_SIZE: {settings.LOG_ROTATION_SIZE}")
   print(f"LOG_BACKUP_COUNT: {settings.LOG_BACKUP_COUNT}")
   ```

2. **Test Logger and Sanitization**:
   ```python
   from app.core.logger import get_logger
   logger = get_logger("debug.test")
   
   # Test basic logging
   logger.info("Basic test message")
   
   # Test sanitization
   logger.info("Test with email: user@example.com and password=secret123")
   
   # Test structured logging
   logger.info("Structured test", extra={
       "user_email": "test@example.com",
       "api_key": "sk_test_12345",
       "component": "debug"
   })
   ```

3. **Verify File Creation and Content**:
   ```bash
   # Check if file exists and recent logs
   ls -la logs/combined.log
   tail -5 logs/combined.log | jq .
   
   # Check rotation files
   ls -la logs/combined.log*
   
   # Monitor real-time logging
   tail -f logs/combined.log | jq 'select(.component == "debug")'
   ```

4. **Test Docker Integration**:
   ```bash
   # Check if containers can write to log volume
   docker-compose -f docker/docker-compose.yml exec api ls -la /app/logs/
   docker-compose -f docker/docker-compose.yml exec worker ls -la /app/logs/
   
   # Test logging from within container
   docker-compose -f docker/docker-compose.yml exec api python -c "
   from app.core.logger import get_logger
   logger = get_logger('docker.test')
   logger.info('Docker container test message')
   "
   ```

## Performance Considerations

### Log Volume Management

- **Buffer Size**: Configured via `LOG_BUFFER_SIZE` (default 1000)
- **Rotation**: Files rotate at `LOG_ROTATION_SIZE` (default 10MB)
- **Retention**: Keep `LOG_BACKUP_COUNT` files (default 5)
- **Total Storage**: Maximum ~50MB with default settings (10MB × 5 backups)

### Enhanced Performance Best Practices

1. **Use Appropriate Log Levels by Environment**:
   ```bash
   # Production
   LOG_LEVEL=INFO
   
   # Staging  
   LOG_LEVEL=INFO
   
   # Development
   LOG_LEVEL=DEBUG  # Only when debugging specific issues
   ```

2. **Efficient Extra Data Structure**:
   ```python
   # GOOD: Simple, relevant values
   logger.info("Campaign processed", extra={
       "campaign_id": campaign.id,
       "leads_processed": 150,
       "duration": 2.34,
       "component": "apollo_service"
   })
   
   # AVOID: Large objects or unnecessary data
   logger.info("Campaign data", extra={
       "full_campaign_object": campaign.__dict__,  # Too large
       "all_leads": leads_list,  # Potentially huge
       "raw_api_response": response_data  # Contains sensitive data
   })
   ```

3. **Smart Logging for High-Volume Operations**:
   ```python
   # For operations processing many items, log summaries rather than each item
   processed_count = 0
   error_count = 0
   
   for lead in leads:
       try:
           process_lead(lead)
           processed_count += 1
       except Exception as e:
           error_count += 1
           # Only log first few errors, then summarize
           if error_count <= 5:
               logger.error(f"Lead processing failed: {e}", extra={
                   "lead_id": lead.id,
                   "component": "lead_processor"
               })
   
   # Log summary
   logger.info("Batch processing completed", extra={
       "total_processed": processed_count,
       "total_errors": error_count,
       "success_rate": processed_count / (processed_count + error_count),
       "component": "lead_processor"
   })
   ```

4. **Conditional Logging for Expensive Operations**:
   ```python
   # Only compute expensive debug info if DEBUG level is enabled
   if logger.isEnabledFor(logging.DEBUG):
       expensive_debug_data = analyze_complex_data(data)
       logger.debug("Complex analysis completed", extra=expensive_debug_data)
   ```

### Monitoring Performance Impact

- **Disk I/O**: Monitor during high log volume periods
- **Memory Usage**: Watch for log buffer accumulation
- **Network Impact**: Consider log forwarding overhead in production
- **CPU Usage**: JSON serialization and sanitization overhead

```bash
# Monitor disk usage
watch -n 5 'df -h logs/ && ls -lah logs/combined.log*'

# Monitor log file growth rate
watch -n 1 'stat logs/combined.log | grep Size'
```

## Integration with External Systems

### Log Aggregation

The enhanced JSON format with correlation IDs and structured metadata makes integration seamless:

**ELK Stack (Elasticsearch, Logstash, Kibana)**:
```yaml
# Filebeat configuration
filebeat.inputs:
- type: log
  paths:
    - "/app/logs/combined.log"
  json.keys_under_root: true
  json.add_error_key: true
  fields:
    service: fastapi-k8-proto
  fields_under_root: true

processors:
- timestamp:
    field: timestamp
    layouts:
      - '2006-01-02T15:04:05.000000Z'
    test:
      - '2025-01-20T10:30:45.123456Z'
```

**Grafana Loki**:
```yaml
# Promtail configuration  
clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
- job_name: fastapi-k8-proto
  static_configs:
  - targets:
      - localhost
    labels:
      job: fastapi-k8-proto
      __path__: /app/logs/combined.log
  pipeline_stages:
  - json:
      expressions:
        level: level
        component: component
        correlation_id: correlation_id
  - labels:
      level:
      component:
```

**Splunk**:
```conf
# inputs.conf
[monitor:///app/logs/combined.log]
disabled = false
sourcetype = json_auto
index = fastapi_logs

# props.conf
[json_auto]
KV_MODE = json
TIME_PREFIX = "timestamp":"
TIME_FORMAT = %Y-%m-%dT%H:%M:%S.%6N%Z
```

### Kubernetes Integration

For Kubernetes deployment with enhanced log correlation:

```yaml
# Fluent-bit DaemonSet configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
data:
  fluent-bit.conf: |
    [INPUT]
        Name              tail
        Path              /app/logs/combined.log
        Parser            json
        Tag               fastapi.*
        Refresh_Interval  5

    [FILTER]
        Name kubernetes
        Match fastapi.*
        Kube_URL https://kubernetes.default.svc:443
        Merge_Log On
        K8S-Logging.Parser On
        K8S-Logging.Exclude Off

    [OUTPUT]
        Name  forward
        Match *
        Host  fluent-aggregator
        Port  24224
```

### Alerting Integration

With structured logging, set up intelligent alerts:

```yaml
# Prometheus AlertManager rules
groups:
- name: fastapi-logging-alerts
  rules:
  - alert: HighErrorRate
    expr: |
      (
        rate(log_entries{level="ERROR"}[5m]) / 
        rate(log_entries[5m])
      ) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value | humanizePercentage }} over the last 5 minutes"

  - alert: CriticalServiceFailure
    expr: log_entries{level="CRITICAL"} > 0
    for: 0m
    labels:
      severity: critical
    annotations:
      summary: "Critical service failure"
      description: "Critical error in {{ $labels.component }}: {{ $labels.message }}"

  - alert: APICreditsExhausted
    expr: |
      increase(log_entries{message=~".*rate limit.*|.*credits.*exhausted.*"}[1h]) > 10
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "API credits running low"
      description: "Multiple rate limit or credit exhaustion messages detected"
```

## Security Considerations

### Enhanced Security Features

1. **Multi-Layer Data Sanitization**:
   - **Automatic**: LogSanitizer with comprehensive patterns
   - **Contextual**: Different sanitization levels per component
   - **Configurable**: Additional patterns can be added as needed

2. **Log File Security**:
   ```bash
   # Set appropriate permissions
   chmod 750 logs/                    # Directory: owner/group read/write/execute
   chmod 640 logs/combined.log*       # Files: owner read/write, group read
   chown app:logging logs/            # Proper ownership
   ```

3. **Sensitive Data Audit**:
   ```bash
   # Regular audit for potentially missed sensitive data
   grep -E "(password|secret|key|token)" logs/combined.log | head -5
   
   # Should only return [REDACTED_*] patterns
   ```

4. **Access Control Implementation**:
   - Implement role-based access to log files
   - Use log aggregation system authentication
   - Rotate log access credentials regularly

### Compliance Considerations

1. **Data Retention Policies**:
   ```bash
   # Automated cleanup for compliance
   find logs/ -name "combined.log.*" -mtime +30 -delete  # Keep 30 days
   ```

2. **Audit Trail**:
   - All configuration changes logged
   - Log access audited through system logs
   - Sanitization effectiveness monitored

3. **Privacy Protection**:
   - Personal data automatically redacted
   - Geographic compliance through log storage location
   - Data subject rights supported through correlation IDs

## Maintenance and Operations

### Regular Maintenance Tasks

1. **Daily**:
   ```bash
   # Check log file sizes and rotation
   ls -lah logs/
   
   # Verify recent logging activity
   tail -1 logs/combined.log | jq .timestamp
   ```

2. **Weekly**:
   ```bash
   # Monitor disk usage trends
   du -sh logs/
   
   # Check for any sanitization failures
   grep -c "\[REDACTED_" logs/combined.log
   
   # Verify log correlation across services
   grep -c "correlation_id" logs/combined.log
   ```

3. **Monthly**:
   ```bash
   # Analyze log patterns and volumes
   jq -r '.component' logs/combined.log* | sort | uniq -c | sort -nr
   
   # Review error patterns
   jq 'select(.level == "ERROR") | .message' logs/combined.log* | sort | uniq -c
   
   # Performance analysis
   jq 'select(.processing_duration) | .processing_duration' logs/combined.log* | \
     awk '{sum+=$1; count++} END {print "Avg:", sum/count, "Max:", max}'
   ```

### Operational Runbooks

#### Log Rotation Issues
```bash
# If rotation fails, manual rotation:
cd logs/
mv combined.log combined.log.manual.$(date +%Y%m%d_%H%M%S)
touch combined.log
chmod 640 combined.log
docker-compose -f docker/docker-compose.yml restart api worker
```

#### Performance Degradation
```bash
# Temporarily reduce log volume:
echo "LOG_LEVEL=WARNING" >> .env
docker-compose -f docker/docker-compose.yml restart api worker

# Monitor improvement:
tail -f logs/combined.log | jq '.level' | uniq -c
```

#### Disk Space Emergency
```bash
# Emergency log cleanup (keep only current):
cd logs/
rm -f combined.log.[0-9]*
# Reduce rotation size temporarily:
echo "LOG_ROTATION_SIZE=5242880" >> .env  # 5MB
```

This comprehensive unified logging system provides enterprise-grade observability with automatic sanitization, structured output, and seamless integration capabilities for the FastAPI K8s prototype application. 