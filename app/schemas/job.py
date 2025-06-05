from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from app.models.job import JobStatus, JobType

class JobBase(BaseModel):
    name: str
    description: Optional[str] = None
    job_type: JobType = JobType.FETCH_LEADS
    campaign_id: Optional[str] = None

class JobCreate(JobBase):
    pass

class JobInDB(JobBase):
    id: int
    task_id: Optional[str] = None
    job_type: JobType
    status: JobStatus
    result: Optional[str] = None
    error: Optional[str] = None
    campaign_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class JobResponse(JobInDB):
    pass