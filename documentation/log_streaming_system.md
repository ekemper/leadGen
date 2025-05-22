# Log Streaming System Documentation

## Overview

The Log Streaming System is a real-time log aggregation and analysis service designed to collect, process, and analyze logs from various components of the LeadGen application. It provides a WebSocket-based interface for real-time log access and supports model-based log analysis.

## Architecture

```
┌─ Log Sources ─────────┐     ┌─ Log Service ──────────┐     ┌─ Consumers ───────┐
│ • Docker Containers   │     │ • Log Collection       │     │ • WebSocket       │
│ • Application Logs    │ ──> │ • Real-time Processing │ ──> │   Clients        │
│ • System Processes    │     │ • Analysis Queue       │     │ • Model Analysis  │
└────────────────────────┘     └──────────────────────┘     └──────────────────┘
```

## Standardized Logging Pattern

### Logger Setup

All components should use the standardized logger setup:

```python
from server.utils.logging_config import setup_logger, ContextLogger

# Set up component-specific logger
logger = setup_logger('component_name')
```

### Logging Context

Use the ContextLogger to add contextual information to logs:

```python
with ContextLogger(logger, **context):
    logger.info("Operation started", extra={
        'metadata': {
            'key': 'value'
        }
    })
```

### Log Format

All logs follow a standardized JSON format:
```json
{
    "timestamp": "2024-03-21T10:30:00.123Z",
    "level": "INFO",
    "source": "component_name",
    "message": "Log message",
    "context": {
        "request_id": "uuid",
        "user_id": "user_uuid",
        "additional_context": "value"
    },
    "metadata": {
        "operation_specific": "data"
    }
}
```

### Log Levels

- ERROR: For errors that prevent normal operation
- WARNING: For concerning but non-fatal issues
- INFO: For normal operational events
- DEBUG: For detailed debugging information

### Best Practices

1. **Structured Logging**
   - Always use structured logging with context and metadata
   - Include relevant identifiers (request_id, user_id, etc.)
   - Use consistent field names across components

2. **Error Handling**
   ```python
   try:
       operation()
   except Exception as e:
       logger.error("Operation failed", extra={
           'metadata': {
               'error': str(e)
           }
       }, exc_info=True)
   ```

3. **Context Management**
   - Use ContextLogger for operation-specific context
   - Maintain context across asynchronous boundaries
   - Include relevant business context

4. **Sensitive Data**
   - Use LogSanitizer to redact sensitive information
   - Never log credentials, tokens, or personal data
   - Configure sanitization patterns per environment

5. **Performance**
   - Use appropriate log levels
   - Avoid logging large payloads
   - Consider log rotation and retention policies

## Components

### 1. Log Service

- Collects logs from all components
- Provides real-time streaming via WebSocket
- Supports log filtering and analysis
- Handles log rotation and archival

### 2. Docker Log Collector

- Captures logs from Docker containers
- Standardizes container log formats
- Provides container-specific context

### 3. Application Log Collector

- Collects logs from Flask application
- Handles web request logging
- Manages application-specific context

### 4. Background Services

- Worker process logging
- Task execution logging
- Asynchronous operation tracking

## Configuration

### Environment Variables

```env
LOG_DIR=./logs
LOG_LEVEL=INFO
LOG_ROTATION_SIZE=10485760  # 10MB
LOG_BACKUP_COUNT=5
LOG_SERVICE_HOST=localhost
LOG_SERVICE_PORT=8765
LOG_BUFFER_SIZE=1000
```

### Log Rotation

- Maximum file size: 10MB
- Backup count: 5 files
- Rotation format: {filename}.{timestamp}.log

### Service Configuration

```python
DOCKER_SERVICES = {
    'backend': {
        'port': 5001,
        'log_type': 'application',
        'healthcheck': '/api/health'
    },
    'worker': {
        'log_type': 'background',
        'healthcheck': None
    }
    # ... additional services
}
```

## Integration

### 1. Flask Application

```python
from server.utils.logging_config import setup_logger, ContextLogger

logger = setup_logger('flask.app')

@app.route('/api/endpoint')
def endpoint():
    with ContextLogger(logger, endpoint='/api/endpoint'):
        try:
            # Operation logic
            logger.info("Operation successful", extra={
                'metadata': {'operation_data': 'value'}
            })
        except Exception as e:
            logger.error("Operation failed", extra={
                'metadata': {'error': str(e)}
            }, exc_info=True)
```

### 2. Background Workers

```python
from server.utils.logging_config import setup_logger, ContextLogger

logger = setup_logger('worker')

def worker_task():
    with ContextLogger(logger, task_id='unique_id'):
        logger.info("Task started", extra={
            'metadata': {'task_data': 'value'}
        })
        # Task logic
```

### 3. Frontend Integration

```typescript
class Logger {
    private static instance: Logger;
    private logQueue: LogEntry[] = [];
    
    log(level: string, message: string, context?: object) {
        const logEntry = {
            timestamp: new Date().toISOString(),
            level,
            message,
            context,
            source: 'frontend'
        };
        this.queue(logEntry);
    }
}
```

## Monitoring and Analysis

- Real-time log streaming via WebSocket
- Log analysis and pattern detection
- Error rate monitoring and alerting
- Performance metrics collection

## Security

- Log sanitization for sensitive data
- Authentication for log access
- Encryption for log transmission
- Role-based access control

## Maintenance

- Regular log rotation
- Automated cleanup of old logs
- Performance monitoring
- Storage optimization

## Setup

### Environment Variables

```bash
LOG_SERVICE_HOST=localhost      # Log service host
LOG_SERVICE_PORT=8765          # Log service port
LOG_BUFFER_SIZE=1000           # Number of logs to keep in memory
LOG_DIR=./logs                 # Directory for log files
LOG_LEVEL=INFO                 # Default log level
LOG_MAX_BYTES=10485760        # Max log file size (10MB)
LOG_BACKUP_COUNT=5            # Number of backup files to keep
```

### Docker Integration

Add to docker-compose.yml:

```yaml
services:
  log-service:
    build:
      context: .
      dockerfile: Dockerfile.log-service
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./logs:/app/logs
    ports:
      - "8765:8765"
    environment:
      - LOG_SERVICE_HOST=0.0.0.0
      - LOG_SERVICE_PORT=8765
      - LOG_BUFFER_SIZE=1000
      - LOG_DIR=/app/logs
      - LOG_LEVEL=INFO
```

## Usage

### Connecting to the Log Stream

```python
import websockets
import json
import asyncio

async def connect_to_logs():
    async with websockets.connect('ws://localhost:8765') as websocket:
        # Receive log stream
        async for message in websocket:
            log_entry = json.loads(message)
            print(f"{log_entry['timestamp']} - {log_entry['service_name']}: {log_entry['content']}")

asyncio.run(connect_to_logs())
```

### Requesting Log Analysis

```python
async def request_analysis(websocket):
    analysis_request = {
        'type': 'analysis_request',
        'request_id': 'unique_id',
        'time_range': 3600,  # Last hour
        'service': 'backend',  # Optional service filter
        'level': 'ERROR'      # Optional level filter
    }
    await websocket.send(json.dumps(analysis_request))
    response = await websocket.recv()
    return json.loads(response)
```

## Log Entry Format

### Standard Log Entry

```json
{
    "timestamp": "2024-03-21T10:30:00",
    "source": "docker",
    "stream": "stdout",
    "content": "Log message content",
    "level": "INFO",
    "service_name": "backend",
    "metadata": {
        "container_id": "abc123"
    },
    "context": {
        "service_type": "application"
    }
}
```

### Model Context Format

```json
{
    "time": "2024-03-21T10:30:00",
    "source": "docker",
    "content": "Log message content",
    "level": "INFO",
    "service": "backend",
    "context": {
        "service_type": "application",
        "container_id": "abc123"
    }
}
```

## Integration with Model Analysis

The log streaming system is designed to work seamlessly with model-based analysis:

1. **Real-time Analysis**
   - Logs are automatically formatted for model consumption
   - Context preservation for better analysis
   - Support for batch and stream processing

2. **Analysis Triggers**
   - Error detection
   - Pattern matching
   - Resource threshold monitoring

3. **Context Management**
   - Historical log context
   - Service relationships
   - System state information

## Best Practices

### 1. Logger Creation and Usage

```python
# Create module-specific logger
logger = setup_logger('module_name')

# DO: Use structured logging with context
logger.info("User action completed", extra={
    'metadata': {'action': 'login'},
    'context': {'user_id': 123}
})

# DON'T: Use string formatting for sensitive data
logger.info(f"User {email} logged in")  # WRONG
logger.info("User logged in", extra={'metadata': {'email': email}})  # RIGHT
```

### 2. Context Management

```python
# DO: Use context manager for request handling
@app.route('/api/resource')
def handle_request():
    with ContextLogger(logger, 
                      request_id=request.headers.get('X-Request-ID'),
                      endpoint='/api/resource'):
        # All logs in this block will include the context
        logger.info("Processing request")
        # ... handle request ...
        logger.info("Request completed")

# DON'T: Manually add context to each log
logger.info("Message", extra={'context': {...}})  # WRONG
```

### 3. Error Handling

```python
# DO: Include error context and use appropriate log levels
try:
    # ... operation ...
except Exception as e:
    logger.error("Operation failed", 
                 extra={
                     'error': str(e),
                     'stack_trace': traceback.format_exc()
                 },
                 exc_info=True)

# DON'T: Log sensitive error details directly
logger.error(f"Failed to process payment for {card_number}")  # WRONG
```

### 4. Performance Considerations

- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR)
- Implement log rotation to manage disk space
- Buffer logs appropriately in high-throughput scenarios

### 5. Security

- All sensitive data is automatically sanitized
- Logs are stored securely with appropriate permissions
- Access to log streams is authenticated and authorized

## Troubleshooting

### Common Issues

1. **Missing Context**
   - Ensure ContextLogger is used for request handling
   - Check context propagation in async operations
   - Verify context cleanup in error cases

2. **Performance Issues**
   - Check log levels (too many DEBUG logs?)
   - Monitor log file sizes and rotation
   - Review log buffer configuration

3. **Security Concerns**
   - Verify sensitive data patterns in LogSanitizer
   - Check log file permissions
   - Review log access patterns

## Development

### Adding New Log Sources

1. Create a new collector class:
```python
class NewSourceCollector:
    def __init__(self, config):
        self.logger = setup_logger('new_source_collector')
        # ... initialization ...

    async def collect(self):
        with ContextLogger(self.logger, source='new_source'):
            # ... collection logic ...
```

### Extending Log Analysis

1. Add new analysis capabilities:
```python
class LogAnalyzer:
    def __init__(self):
        self.logger = setup_logger('log_analyzer')

    async def analyze(self, logs, criteria):
        with ContextLogger(self.logger, analysis_type='custom'):
            # ... analysis logic ...
```

## Migration Guide

When migrating from old logging patterns:

1. Replace direct logger creation:
```python
# Old
logger = logging.getLogger(__name__)

# New
logger = setup_logger(__name__)
```

2. Update log formatting:
```python
# Old
logger.info(f"Processing {item}")

# New
logger.info("Processing item", extra={'metadata': {'item': item}})
```

3. Add context management:
```python
# Old
logger.info("Message", extra={'request_id': req_id})

# New
with ContextLogger(logger, request_id=req_id):
    logger.info("Message")
```

## Monitoring and Maintenance

1. **Health Checks**
   - WebSocket server status
   - Collector operations
   - Analysis queue length

2. **Metrics**
   - Log volume per source
   - Analysis request rate
   - Response times

3. **Maintenance Tasks**
   - Log rotation
   - Buffer cleanup
   - Connection management

## Testing

### Unit Tests

The logging system includes comprehensive unit tests in `server/tests/test_logging.py`:

1. **Log Format Tests**
   - Verify required fields are present
   - Check field value correctness
   - Validate JSON structure

2. **Context Management Tests**
   - Test nested context handling
   - Verify context inheritance
   - Check context cleanup

3. **Sanitization Tests**
   - Verify sensitive data redaction
   - Test pattern matching
   - Check field-based sanitization

4. **Error Handling Tests**
   - Test exception logging
   - Verify stack trace capture
   - Check error context preservation

### Integration Tests

When implementing new logging features:

1. **Component Integration**
   ```python
   def test_component_logging():
       with ContextLogger(logger, component='test'):
           # Component operations
           assert_logs_contain_context()
   ```

2. **Cross-Service Logging**
   - Test context propagation
   - Verify log aggregation
   - Check service identification

3. **Performance Testing**
   - Measure logging impact
   - Test under high load
   - Verify log rotation

### Test Environment

```python
@pytest.fixture(autouse=True)
def setup_test_logs():
    """Setup temporary log directory for tests."""
    test_log_dir = tempfile.mkdtemp()
    os.environ['LOG_DIR'] = test_log_dir
    yield
    shutil.rmtree(test_log_dir)
```

### Mocking Guidelines

1. **Logger Mocking**
   ```python
   @pytest.fixture
   def mock_logger():
       with patch('server.utils.logging_config.setup_logger') as mock:
           yield mock
   ```

2. **Context Verification**
   ```python
   def verify_log_context(log_entry, expected_context):
       assert all(item in log_entry['context'].items() 
                 for item in expected_context.items())
   ``` 