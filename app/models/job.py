from sqlalchemy import Column, Integer, String, DateTime, Enum, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base

class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PAUSED = "PAUSED"

class JobType(str, enum.Enum):
    """Campaign-specific job types for different operations."""
    FETCH_LEADS = "FETCH_LEADS"
    ENRICH_LEAD = "ENRICH_LEAD"
    CLEANUP_CAMPAIGN = "CLEANUP_CAMPAIGN"

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    job_type = Column(Enum(JobType), default=JobType.FETCH_LEADS, nullable=False, index=True)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)
    result = Column(Text)
    error = Column(Text)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Relationship to campaign
    campaign = relationship("Campaign", back_populates="jobs") 