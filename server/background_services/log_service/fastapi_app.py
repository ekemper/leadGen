import os
import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Set
from collections import deque
from .models import LogEntry
from .collectors import DockerLogCollector, ApplicationLogCollector

app = FastAPI()

# Allow CORS for local dev tools
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Config
LOG_BUFFER_SIZE = int(os.getenv("LOG_BUFFER_SIZE", 1000))
LOG_DIR = os.getenv("LOG_DIR", "./logs")
DOCKER_SERVICES = {
    'backend': {'log_type': 'application'},
    'worker': {'log_type': 'background'},
    'frontend': {'log_type': 'frontend'},
    'redis': {'log_type': 'database'},
    'db': {'log_type': 'database'}
}

log_buffer = deque(maxlen=LOG_BUFFER_SIZE)
active_websockets: Set[WebSocket] = set()
log_broadcast_lock = asyncio.Lock()
analysis_queue = asyncio.Queue()

# --- Health Check ---
@app.get("/health")
async def health():
    return JSONResponse(content={"status": "healthy"})

# --- WebSocket Endpoint ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.add(websocket)
    try:
        # Send buffer history
        for log in log_buffer:
            await websocket.send_text(json.dumps(log.to_dict()))
        # Listen for messages
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get('type') == 'analysis_request':
                    await analysis_queue.put({'client': websocket, 'request': msg})
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid message format"}))
    except WebSocketDisconnect:
        pass
    finally:
        active_websockets.discard(websocket)

# --- Log Broadcasting ---
async def broadcast_log(log_entry: LogEntry):
    log_buffer.append(log_entry)
    message = json.dumps(log_entry.to_dict())
    async with log_broadcast_lock:
        disconnected = set()
        for ws in active_websockets:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.add(ws)
        for ws in disconnected:
            active_websockets.discard(ws)

# --- Analysis Worker ---
async def analysis_worker():
    while True:
        req = await analysis_queue.get()
        try:
            client = req['client']
            analysis_request = req['request']
            # Prepare context for analysis (simple filter on buffer)
            time_range = analysis_request.get('time_range', 3600)
            service_filter = analysis_request.get('service')
            level_filter = analysis_request.get('level')
            from datetime import datetime
            now = datetime.now()
            filtered_logs = [
                log for log in log_buffer
                if (now - log.timestamp).total_seconds() <= time_range
                and (not service_filter or log.service_name == service_filter)
                and (not level_filter or log.level == level_filter)
            ]
            context = {
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
            if client in active_websockets:
                await client.send_text(json.dumps({
                    'type': 'analysis_response',
                    'request_id': analysis_request.get('request_id'),
                    'context': context
                }))
        except Exception as e:
            print(f"Error processing analysis request: {e}")
        finally:
            analysis_queue.task_done()

# --- Log Collectors Integration ---
async def docker_log_collector_task():
    collector = DockerLogCollector(DOCKER_SERVICES)
    async for log_entry in collector.stream_all_logs():
        await broadcast_log(log_entry)

async def app_log_collector_task():
    collector = ApplicationLogCollector(LOG_DIR)
    await collector.start()  # Start the file watcher
    async for log_entry in collector.stream_all_logs():
        await broadcast_log(log_entry)

async def collector_stream(collector):
    # This assumes the collector yields LogEntry objects
    while True:
        try:
            async for log in collector.collect_container_logs():
                yield log
        except Exception as e:
            print(f"Collector error: {e}")
            await asyncio.sleep(5)

async def app_collector_stream(collector):
    # This assumes the collector yields LogEntry objects
    while True:
        try:
            # You may need to adapt this to your ApplicationLogCollector
            # For now, this is a placeholder for a generator
            await asyncio.sleep(1)
        except Exception as e:
            print(f"App collector error: {e}")
            await asyncio.sleep(5)

# --- Startup/Shutdown Events ---
@app.on_event("startup")
async def startup_event():
    # Start log collectors and analysis worker
    asyncio.create_task(docker_log_collector_task())
    asyncio.create_task(app_log_collector_task())
    asyncio.create_task(analysis_worker())

@app.on_event("shutdown")
async def shutdown_event():
    # Optionally, clean up resources
    pass 