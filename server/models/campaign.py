from datetime import datetime
import uuid
from server.config.database import db
from server.utils.logging_config import server_logger, combined_logger
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
    status_error = db.Column(db.Text, nullable=True)
    job_status = db.Column(JSON, nullable=True)
    job_ids = db.Column(JSON, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __init__(self, name=None, description=None, organization_id=None, id=None, created_at=None, status=None, 
                 status_message=None, status_error=None, job_status=None, job_ids=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.created_at = created_at or datetime.utcnow()
        self.organization_id = organization_id
        self.status = status or CampaignStatus.CREATED
        self.status_message = status_message
        self.status_error = status_error
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
            self.status_message = message
            self.status_error = error
            db.session.commit()
            server_logger.info(f"Campaign {self.id} status updated to {status}", extra={
                'component': 'server',
                'campaign_id': self.id,
                'status': status,
                'message': message,
                'error': error
            })
            combined_logger.info(f"Campaign {self.id} status updated to {status}", extra={
                'component': 'server',
                'campaign_id': self.id,
                'status': status,
                'message': message,
                'error': error
            })
        except Exception as e:
            server_logger.error(f"Error updating campaign status: {str(e)}", extra={
                'component': 'server',
                'campaign_id': self.id,
                'error': str(e)
            })
            combined_logger.error(f"Error updating campaign status: {str(e)}", extra={
                'component': 'server',
                'campaign_id': self.id,
                'error': str(e)
            })
            db.session.rollback()
            raise

    def update_job_status(self, job_id: str, status: str) -> None:
        """
        Update the status of a specific job.
        
        Args:
            job_id: The ID of the job
            status: The new status
        """
        try:
            if job_id in self.job_ids:
                self.job_ids[job_id]['status'] = status
                db.session.commit()
                server_logger.info(f"Campaign {self.id} job {job_id} status updated to {status}", extra={
                    'component': 'server',
                    'campaign_id': self.id,
                    'job_id': job_id,
                    'status': status
                })
                combined_logger.info(f"Campaign {self.id} job {job_id} status updated to {status}", extra={
                    'component': 'server',
                    'campaign_id': self.id,
                    'job_id': job_id,
                    'status': status
                })
        except Exception as e:
            server_logger.error(f"Error updating job status: {str(e)}", extra={
                'component': 'server',
                'campaign_id': self.id,
                'job_id': job_id,
                'error': str(e)
            })
            combined_logger.error(f"Error updating job status: {str(e)}", extra={
                'component': 'server',
                'campaign_id': self.id,
                'job_id': job_id,
                'error': str(e)
            })
            db.session.rollback()
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
            self.job_ids[job_id] = {
                'type': job_type,
                'status': 'pending'
            }
            db.session.commit()
            server_logger.info(f"Campaign {self.id} added job {job_id} of type {job_type}", extra={
                'component': 'server',
                'campaign_id': self.id,
                'job_id': job_id,
                'job_type': job_type
            })
            combined_logger.info(f"Campaign {self.id} added job {job_id} of type {job_type}", extra={
                'component': 'server',
                'campaign_id': self.id,
                'job_id': job_id,
                'job_type': job_type
            })
        except Exception as e:
            server_logger.error(f"Error adding job ID: {str(e)}", extra={
                'component': 'server',
                'campaign_id': self.id,
                'job_id': job_id,
                'job_type': job_type,
                'error': str(e)
            })
            combined_logger.error(f"Error adding job ID: {str(e)}", extra={
                'component': 'server',
                'campaign_id': self.id,
                'job_id': job_id,
                'job_type': job_type,
                'error': str(e)
            })
            db.session.rollback()
            raise

    def to_dict(self) -> Dict[str, Any]:
        """Convert campaign to dictionary representation."""
        try:
            return {
                'id': self.id,
                'name': self.name,
                'description': self.description,
                'organization_id': self.organization_id,
                'status': self.status.value if self.status else None,
                'status_message': self.status_message,
                'status_error': self.status_error,
                'job_ids': self.job_ids,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None
            }
        except Exception as e:
            server_logger.error(f'Error converting campaign {self.id} to dict: {str(e)}', extra={
                'component': 'server',
                'campaign_id': self.id,
                'error': str(e)
            })
            combined_logger.error(f'Error converting campaign {self.id} to dict: {str(e)}', extra={
                'component': 'server',
                'campaign_id': self.id,
                'error': str(e)
            })
            raise

    def __repr__(self) -> str:
        return f'<Campaign {self.id}>' 