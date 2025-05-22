import asyncio
import docker
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, AsyncGenerator
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .models import LogEntry

class DockerLogCollector:
    def __init__(self, service_config: Dict[str, Dict]):
        self.docker_client = docker.from_env()
        self.service_config = service_config
        self.container_tasks = {}

    async def start(self):
        """Start collecting logs from all configured Docker services"""
        while True:
            try:
                containers = self.docker_client.containers.list()
                for container in containers:
                    service_name = self._get_service_name(container)
                    if service_name in self.service_config and container.id not in self.container_tasks:
                        async def run_collector(container=container, service_name=service_name):
                            async for log_entry in self.collect_container_logs(container, service_name):
                                # Optionally, process log_entry here (e.g., send to a queue or broadcast)
                                pass
                        task = asyncio.create_task(run_collector())
                        self.container_tasks[container.id] = task
                
                # Clean up finished tasks
                for container_id in list(self.container_tasks.keys()):
                    if self.container_tasks[container_id].done():
                        del self.container_tasks[container_id]
                
                await asyncio.sleep(10)  # Check for new containers every 10 seconds
            except Exception as e:
                print(f"Error in Docker log collection: {e}")
                await asyncio.sleep(5)

    async def collect_container_logs(self, container, service_name: str) -> AsyncGenerator[LogEntry, None]:
        try:
            config = self.service_config[service_name]
            logs = container.logs(stream=True, follow=True, timestamps=True)
            
            for log in logs:
                try:
                    timestamp_str, message = log.decode().split(" ", 1)
                    timestamp = datetime.fromisoformat(timestamp_str.rstrip('Z'))
                    
                    yield LogEntry(
                        timestamp=timestamp,
                        source='docker',
                        stream='stdout',
                        content=message.strip(),
                        metadata={'container_id': container.id},
                        context={'service_type': config.get('log_type', 'service')},
                        service_name=service_name
                    )
                except Exception as e:
                    print(f"Error processing log from {service_name}: {e}")
        except Exception as e:
            print(f"Error collecting logs from {service_name}: {e}")

    def _get_service_name(self, container) -> Optional[str]:
        """Extract service name from container labels"""
        labels = container.labels
        compose_service = labels.get('com.docker.compose.service')
        return compose_service

    async def stream_all_logs(self):
        """Async generator yielding LogEntry objects from all relevant containers."""
        seen = set()
        while True:
            containers = self.docker_client.containers.list()
            for container in containers:
                service_name = self._get_service_name(container)
                if service_name in self.service_config:
                    try:
                        logs = container.logs(stream=True, follow=True, timestamps=True)
                        for log in logs:
                            try:
                                timestamp_str, message = log.decode().split(" ", 1)
                                timestamp = datetime.fromisoformat(timestamp_str.rstrip('Z'))
                                yield LogEntry(
                                    timestamp=timestamp,
                                    source='docker',
                                    stream='stdout',
                                    content=message.strip(),
                                    metadata={'container_id': container.id},
                                    context={'service_type': self.service_config[service_name].get('log_type', 'service')},
                                    service_name=service_name
                                )
                            except Exception as e:
                                print(f"Error processing log from {service_name}: {e}")
                    except Exception as e:
                        print(f"Error collecting logs from {service_name}: {e}")
            await asyncio.sleep(10)

class LogFileHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback
        super().__init__()

    def on_modified(self, event):
        if not event.is_directory:
            self.callback(event.src_path)

class ApplicationLogCollector:
    def __init__(self, log_dir: str):
        self.log_dir = Path(log_dir)
        self.watchers = {}
        self.observer = Observer()
        self.log_positions = {}
        self.log_queue = asyncio.Queue()

    async def start(self):
        """Start watching log files"""
        event_handler = LogFileHandler(self.handle_log_update)
        self.observer.schedule(event_handler, str(self.log_dir), recursive=False)
        self.observer.start()

    def handle_log_update(self, log_path: str):
        """Handle updates to log files"""
        try:
            with open(log_path, 'r') as f:
                # Seek to last known position
                last_position = self.log_positions.get(log_path, 0)
                f.seek(last_position)
                # Read new lines
                new_lines = f.readlines()
                current_position = f.tell()
                self.log_positions[log_path] = current_position
                # Process new lines
                for line in new_lines:
                    try:
                        log_data = json.loads(line)
                        log_entry = LogEntry(
                            timestamp=datetime.fromisoformat(log_data.get('timestamp', datetime.now().isoformat())),
                            source='application',
                            stream='file',
                            content=log_data.get('message', ''),
                            metadata=log_data.get('metadata', {}),
                            context=log_data.get('context', {}),
                            level=log_data.get('level', 'INFO'),
                            service_name=Path(log_path).stem
                        )
                        asyncio.create_task(self.log_queue.put(log_entry))
                    except json.JSONDecodeError:
                        log_entry = LogEntry(
                            timestamp=datetime.now(),
                            source='application',
                            stream='file',
                            content=line.strip(),
                            metadata={},
                            context={'log_path': log_path},
                            level='INFO',
                            service_name=Path(log_path).stem
                        )
                        asyncio.create_task(self.log_queue.put(log_entry))
        except Exception as e:
            print(f"Error processing log file {log_path}: {e}")

    async def stream_all_logs(self):
        """Async generator yielding LogEntry objects as they are detected from files."""
        while True:
            log_entry = await self.log_queue.get()
            yield log_entry

    def stop(self):
        """Stop watching log files"""
        self.observer.stop()
        self.observer.join() 