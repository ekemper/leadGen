import os
import sys
from rq import Worker, Queue, Connection
from redis import Redis
from server.app import create_app

# Create Flask app context
flask_app = create_app()

# Configure Redis connection
redis_conn = Redis()

if __name__ == '__main__':
    with Connection(redis_conn):
        worker = Worker([Queue()])
        worker.work() 