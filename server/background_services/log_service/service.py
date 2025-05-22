import asyncio
import json
import signal
import websockets
from collections import deque
from datetime import datetime
from typing import Dict, Set, Optional
from .models import LogEntry
from .collectors import DockerLogCollector, ApplicationLogCollector

class LogStreamService:
    def __init__(self, config: dict):
        self.config = config
        self.log_buffer = deque(maxlen=config.get('buffer_size', 1000))
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.docker_collector = DockerLogCollector(config.get('docker_services', {}))
        self.app_collector = ApplicationLogCollector(config.get('log_dir', './logs'))
        self.analysis_queue = asyncio.Queue()
        self.health_route = "/health"
        self.shutdown_event = asyncio.Event()
        self.tasks = set()
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 8765)
        
    async def start(self):
        """Start the log service"""
        # Start collectors
        await self.docker_collector.start()
        await self.app_collector.start()

        # Start websocket server
        async with websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            process_request=self.process_http_request,
            ping_interval=30,
            ping_timeout=10
        ) as server:
            await server.wait_closed()

        # Stop collectors
        await self.docker_collector.stop()
        await self.app_collector.stop()

    async def shutdown(self, signal):
        """Handle shutdown signal"""
        print(f"Received exit signal {signal.name}...")
        self.shutdown_event.set()

    async def process_http_request(self, path: str, request_headers):
        """Handle HTTP requests (for health checks)"""
        if path == self.health_route:
            response = {
                'status': 'healthy',
                'collectors': {
                    'docker': bool(self.docker_collector.container_tasks),
                    'application': bool(self.app_collector.observer.is_alive())
                },
                'clients': len(self.clients),
                'buffer_size': len(self.log_buffer)
            }
            return None  # Let websockets handle the response
            
        # For WebSocket upgrade requests
        if (
            path == "/" and 
            request_headers.get("Upgrade", "").lower() == "websocket" and
            request_headers.get("Connection", "").lower() == "upgrade"
        ):
            return None  # Let websockets handle WebSocket upgrades
            
        # For all other HTTP requests
        return None  # Let websockets handle the response with a 404

    async def handle_client(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Handle WebSocket client connection"""
        try:
            # Register client
            self.clients.add(websocket)
            
            # Send buffer history
            for log in self.log_buffer:
                await websocket.send(json.dumps(log.to_dict()))
            
            # Handle client messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    if data.get('type') == 'analysis_request':
                        await self.analysis_queue.put({
                            'client': websocket,
                            'request': data
                        })
                except json.JSONDecodeError:
                    print(f"Invalid message format: {message}")
                
        except websockets.exceptions.ConnectionClosed:
            print("Client connection closed")
        finally:
            self.clients.remove(websocket)

    async def broadcast_log(self, log_entry: LogEntry):
        """Broadcast log entry to all connected clients"""
        self.log_buffer.append(log_entry)
        message = json.dumps(log_entry.to_dict())
        
        disconnected_clients = set()
        for client in self.clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
        
        # Clean up disconnected clients
        self.clients -= disconnected_clients

    async def analysis_worker(self):
        """Process log analysis requests"""
        while True:
            request = await self.analysis_queue.get()
            try:
                client = request['client']
                analysis_request = request['request']
                
                # Prepare context for analysis
                context = self._prepare_analysis_context(analysis_request)
                
                # Send analysis result
                if client in self.clients:  # Check if client is still connected
                    await client.send(json.dumps({
                        'type': 'analysis_response',
                        'request_id': analysis_request.get('request_id'),
                        'context': context
                    }))
            except Exception as e:
                print(f"Error processing analysis request: {e}")
            finally:
                self.analysis_queue.task_done()

    def _prepare_analysis_context(self, request: dict) -> dict:
        """Prepare context for log analysis"""
        # Get relevant logs based on request parameters
        time_range = request.get('time_range', 3600)  # Default 1 hour
        service_filter = request.get('service')
        level_filter = request.get('level')
        
        current_time = datetime.now()
        filtered_logs = [
            log for log in self.log_buffer
            if (current_time - log.timestamp).total_seconds() <= time_range
            and (not service_filter or log.service_name == service_filter)
            and (not level_filter or log.level == level_filter)
        ]
        
        return {
            'logs': [log.to_model_context() for log in filtered_logs],
            'metadata': {
                'total_logs': len(filtered_logs),
                'time_range': time_range,
                'filters': {
                    'service': service_filter,
                    'level': level_filter
                }
            }
        } 