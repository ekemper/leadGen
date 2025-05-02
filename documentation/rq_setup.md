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

RQ jobs are enqueued using the helpers in `server/tasks.py`:

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
rq worker
```

This will listen for jobs on the default queue.

---

## 5. Monitoring (Optional)

You can monitor jobs using [RQ Dashboard](https://github.com/eoranged/rq-dashboard):

```
pip install rq-dashboard
rq-dashboard
```

Then visit [http://localhost:9181](http://localhost:9181).

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
- Make sure Redis is running before starting the worker.
- If you change code, restart your RQ workers.
- For advanced scheduling, see [rq-scheduler](https://github.com/rq/rq-scheduler).

---

For more details, see the [RQ documentation](https://python-rq.org/) and [Redis documentation](https://redis.io/docs/). 