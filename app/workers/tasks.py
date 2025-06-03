import time
import random
from datetime import datetime
from celery import current_task
from sqlalchemy.orm import Session

from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.job import Job, JobStatus

@celery_app.task(bind=True, name="process_job")
def process_job(self, job_id: int):
    """
    Simulated long-running task that processes a job
    """
    db: Session = SessionLocal()
    
    try:
        # Update job status to processing
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        job.status = JobStatus.PROCESSING
        job.task_id = self.request.id
        db.commit()
        
        # Simulate work with progress updates
        total_steps = 10
        for i in range(total_steps):
            # Update task state
            current_task.update_state(
                state="PROGRESS",
                meta={
                    "current": i + 1,
                    "total": total_steps,
                    "status": f"Processing step {i + 1}/{total_steps}"
                }
            )
            
            # Simulate work
            time.sleep(random.uniform(1, 3))
            
            # Randomly fail some jobs for testing
            if random.random() < 0.1:  # 10% failure rate
                raise Exception("Random processing error")
        
        # Mark job as completed
        job.status = JobStatus.COMPLETED
        job.result = f"Successfully processed {total_steps} steps"
        job.completed_at = datetime.utcnow()
        db.commit()
        
        return {
            "job_id": job_id,
            "status": "completed",
            "result": job.result
        }
        
    except Exception as e:
        # Mark job as failed
        if job:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
        
        raise
    
    finally:
        db.close()

@celery_app.task(name="health_check")
def health_check():
    """Simple task to verify Celery is working"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()} 