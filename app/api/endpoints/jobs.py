from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import math

from app.core.database import get_db
from app.models.job import Job, JobStatus
from app.schemas.job import JobCreate, JobResponse, JobUpdate
from app.workers.tasks import process_job
from pydantic import BaseModel

# Response models for consistent API structure
class JobListData(BaseModel):
    jobs: List[JobResponse]
    total: int
    page: int
    per_page: int
    pages: int

class JobsListResponse(BaseModel):
    status: str
    data: JobListData

class JobDetailResponse(BaseModel):
    status: str
    data: JobResponse

class JobCreateResponse(BaseModel):
    status: str
    data: JobResponse

class JobUpdateResponse(BaseModel):
    status: str
    data: JobResponse

class JobStatusResponse(BaseModel):
    status: str
    data: dict

class JobCancelResponse(BaseModel):
    status: str
    message: str

router = APIRouter()

@router.post("/", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_in: JobCreate,
    db: Session = Depends(get_db)
):
    """Create a new job and queue it for processing"""
    # Create job in database
    job = Job(
        name=job_in.name,
        description=job_in.description,
        job_type=job_in.job_type,
        campaign_id=job_in.campaign_id,
        status=JobStatus.PENDING
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Queue job for processing
    task = process_job.delay(job.id)
    
    # Update job with task ID
    job.task_id = task.id
    db.commit()
    db.refresh(job)
    
    return JobCreateResponse(
        status="success",
        data=job
    )

@router.get("/", response_model=JobsListResponse)
async def list_jobs(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    status_filter: Optional[JobStatus] = Query(None, alias="status", description="Filter by job status"),
    campaign_id: Optional[str] = Query(None, description="Filter by campaign ID"),
    db: Session = Depends(get_db)
):
    """List all jobs with optional status filter, campaign filter, and pagination"""
    # Build query
    query = db.query(Job)
    if status_filter:
        query = query.filter(Job.status == status_filter)
    if campaign_id:
        query = query.filter(Job.campaign_id == campaign_id)
    
    # Get total count
    total_jobs = query.count()
    
    # Calculate pagination
    total_pages = math.ceil(total_jobs / per_page) if total_jobs > 0 else 1
    skip = (page - 1) * per_page
    
    # Get paginated jobs
    jobs = query.offset(skip).limit(per_page).all()
    
    # Create response data
    data = JobListData(
        jobs=jobs,
        total=total_jobs,
        page=page,
        per_page=per_page,
        pages=total_pages
    )
    
    return JobsListResponse(status="success", data=data)

@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific job by ID"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    return JobDetailResponse(
        status="success",
        data=job
    )

@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: int,
    db: Session = Depends(get_db)
):
    """Get job status including Celery task progress"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    response_data = {
        "id": job.id,
        "status": job.status,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "completed_at": job.completed_at
    }
    
    # Get Celery task status if available
    if job.task_id and job.status == JobStatus.PROCESSING:
        from app.workers.celery_app import celery_app
        task_result = celery_app.AsyncResult(job.task_id)
        
        if task_result.state == "PROGRESS":
            response_data["progress"] = task_result.info
        else:
            response_data["task_state"] = task_result.state
    
    return JobStatusResponse(
        status="success",
        data=response_data
    )

@router.post("/{job_id}/cancel", response_model=JobCancelResponse)
async def cancel_job_post(
    job_id: int,
    db: Session = Depends(get_db)
):
    """Cancel a pending or processing job (POST endpoint)"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    if job.status not in [JobStatus.PENDING, JobStatus.PROCESSING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job in {job.status} status"
        )
    
    # Revoke Celery task if it exists
    if job.task_id:
        from app.workers.celery_app import celery_app
        celery_app.control.revoke(job.task_id, terminate=True)
    
    # Update job status
    job.status = JobStatus.CANCELLED
    db.commit()
    
    return JobCancelResponse(
        status="success",
        message=f"Job {job_id} cancelled"
    )

@router.delete("/{job_id}", response_model=JobCancelResponse)
async def cancel_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """Cancel a pending or processing job"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    if job.status not in [JobStatus.PENDING, JobStatus.PROCESSING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job in {job.status} status"
        )
    
    # Revoke Celery task if it exists
    if job.task_id:
        from app.workers.celery_app import celery_app
        celery_app.control.revoke(job.task_id, terminate=True)
    
    # Update job status
    job.status = JobStatus.CANCELLED
    db.commit()
    
    return JobCancelResponse(
        status="success",
        message=f"Job {job_id} cancelled"
    ) 