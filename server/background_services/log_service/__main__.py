import asyncio
import os
from pathlib import Path

from .service import LogStreamService

def load_config():
    """Load configuration for the log service"""
    return {
        'host': os.getenv('LOG_SERVICE_HOST', 'localhost'),
        'port': int(os.getenv('LOG_SERVICE_PORT', 8765)),
        'buffer_size': int(os.getenv('LOG_BUFFER_SIZE', 1000)),
        'log_dir': os.getenv('LOG_DIR', './logs'),
        'docker_services': {
            'backend': {'log_type': 'application'},
            'worker': {'log_type': 'background'},
            'frontend': {'log_type': 'frontend'},
            'redis': {'log_type': 'database'},
            'db': {'log_type': 'database'}
        }
    }

async def main():
    """Main entry point for the log service"""
    # Ensure log directory exists
    log_dir = Path(os.getenv('LOG_DIR', './logs'))
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize and start service
    config = load_config()
    service = LogStreamService(config)
    
    print(f"Starting log service on {config['host']}:{config['port']}")
    await service.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down log service...") 