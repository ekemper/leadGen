# RQ Setup & Usage Guide

This guide explains how to configure and run [RQ](https://python-rq.org/) for background task processing in the Lead Generation Server.

---

## 1. Install RQ and Redis dependencies

These are already in your `requirements.txt`:

```
pip install rq redis
```

---

## 2. Start Redis

RQ uses Redis as the default broker. Start Redis locally (default port 6379):

```
redis-server
```

---

## 3. RQ Job Queue

RQ jobs are enqueued using the helpers in `server/tasks.py`. The system uses a single queue with the following configuration:

- Queue timeout: 1 hour
- Job timeout: 30 minutes
- Retry delay: 5 minutes
- Maximum retries: 3

Example usage:
```
from server.tasks import enqueue_fetch_and_save_leads, enqueue_email_verification, enqueue_enriching_leads

# Example:
job1 = enqueue_fetch_and_save_leads(params, campaign_id)
job2 = enqueue_email_verification({'campaign_id': campaign_id}, depends_on=job1)
job3 = enqueue_enriching_leads({'campaign_id': campaign_id}, depends_on=job2)
```

---

## 4. Start an RQ Worker

From your project root, run:

```
python server/run_worker.py
```

This will start a worker with the following configuration:
- Processes jobs from the default queue
- Monitors job status every second
- Restarts after processing 1000 jobs (prevents memory leaks)
- Handles graceful shutdown on SIGTERM/SIGINT
- Provides detailed logging with timestamps and process information

---

## 5. Monitoring

### RQ Dashboard
You can monitor jobs using [RQ Dashboard](https://github.com/eoranged/rq-dashboard):

```
pip install rq-dashboard
rq-dashboard
```

Then visit [http://localhost:9181](http://localhost:9181).

### Logging

The worker uses the **central logger**, so every job event is emitted both to Docker `stdout` and to the shared `logs/combined.log` file.  Expect JSON lines similar to:

```json
{"timestamp": "2025-05-24T12:35:00Z", "level": "INFO", "name": "worker", "message": "Started job 123", "component": "rq"}
```

`worker.log` is no longer created; grep `combined.log` or run `docker compose logs -f worker` for live output.

---

## 6. Job Chaining

RQ supports job dependencies for chaining:

```
job1 = enqueue_fetch_and_save_leads(params, campaign_id)
job2 = enqueue_email_verification({'campaign_id': campaign_id}, depends_on=job1)
job3 = enqueue_enriching_leads({'campaign_id': campaign_id}, depends_on=job2)
```

Each job will only run after its dependency completes successfully.

---

## 7. Troubleshooting
- Make sure Redis is running before starting the worker
- If you change code, restart your RQ workers
- Check the logs for any job failures or retries
- Monitor job timeouts and adjust configuration if needed
- Check `logs/combined.log` or `docker compose logs worker` for detailed error information
- Monitor worker restarts (occurs every 1000 jobs)

---

For more details, see the [RQ documentation](https://python-rq.org/) and [Redis documentation](https://redis.io/docs/). 