from datetime import datetime
import uuid
from server.config.database import db
import logging
from sqlalchemy.dialects.postgresql import JSON
from enum import Enum
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class CampaignStatus(str, Enum):
    """Enum for campaign status values."""
    CREATED = 'created'
    FETCHING_LEADS = 'fetching_leads'
    LEADS_FETCHED = 'leads_fetched'
    ENRICHING = 'enriching'
    ENRICHED = 'enriched'
    VERIFYING_EMAILS = 'verifying_emails'
    EMAILS_VERIFIED = 'emails_verified'
    GENERATING_EMAILS = 'generating_emails'
    COMPLETED = 'completed'
    FAILED = 'failed'

class Campaign(db.Model):
    __tablename__ = 'campaigns'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'), nullable=False)
    status = db.Column(db.String(50), default=CampaignStatus.CREATED, nullable=False)
    status_message = db.Column(db.Text, nullable=True)
    last_error = db.Column(db.Text, nullable=True)
    job_status = db.Column(JSON, nullable=True)
    job_ids = db.Column(JSON, nullable=True)

    def __init__(self, name=None, description=None, organization_id=None, id=None, created_at=None, status=None, 
                 status_message=None, last_error=None, job_status=None, job_ids=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.created_at = created_at or datetime.utcnow()
        self.organization_id = organization_id
        self.status = status or CampaignStatus.CREATED
        self.status_message = status_message
        self.last_error = last_error
        self.job_status = job_status or {}
        self.job_ids = job_ids or {}

    def update_status(self, status: CampaignStatus, message: Optional[str] = None, error: Optional[str] = None) -> None:
        """
        Update the campaign status and related fields.
        
        Args:
            status: The new status from CampaignStatus enum
            message: Optional status message
            error: Optional error message
        """
        try:
            self.status = status
            if message:
                self.status_message = message
            if error:
                self.last_error = error
            db.session.commit()
            logger.info(f"Campaign {self.id} status updated to {status}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating campaign status: {str(e)}")
            raise

    def update_job_status(self, job_id: str, status: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Update the status of a specific job.
        
        Args:
            job_id: The ID of the job
            status: The new status
            details: Optional additional details about the job
        """
        try:
            if not self.job_status:
                self.job_status = {}
            self.job_status[job_id] = {
                'status': status,
                'updated_at': datetime.utcnow().isoformat(),
                'details': details or {}
            }
            db.session.commit()
            logger.info(f"Campaign {self.id} job {job_id} status updated to {status}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating job status: {str(e)}")
            raise

    def add_job_id(self, job_type: str, job_id: str) -> None:
        """
        Add a job ID to track.
        
        Args:
            job_type: The type of job (e.g., 'fetch_leads', 'enrich_leads')
            job_id: The ID of the job
        """
        try:
            if not self.job_ids:
                self.job_ids = {}
            self.job_ids[job_type] = job_id
            db.session.commit()
            logger.info(f"Campaign {self.id} added job {job_id} of type {job_type}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding job ID: {str(e)}")
            raise

    def to_dict(self) -> Dict[str, Any]:
        """Convert campaign to dictionary representation."""
        try:
            return {
                'id': self.id,
                'name': self.name,
                'description': self.description,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'organization_id': self.organization_id,
                'status': self.status,
                'status_message': self.status_message,
                'last_error': self.last_error,
                'job_status': self.job_status,
                'job_ids': self.job_ids
            }
        except Exception as e:
            logger.error(f'Error converting campaign {self.id} to dict: {str(e)}')
            raise

    def __repr__(self) -> str:
        return f'<Campaign {self.id}>' 