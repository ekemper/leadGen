from datetime import datetime
import uuid
import logging
from server.config.database import db
from server.utils.logging_config import server_logger
from sqlalchemy.dialects.postgresql import JSON
from enum import Enum
from typing import Dict, Any, Optional
from server.models.campaign_status import CampaignStatus
from server.models.job import Job
from server.utils.error_messages import CAMPAIGN_ERRORS, JOB_ERRORS

logger = logging.getLogger(__name__)

class Campaign(db.Model):
    __tablename__ = 'campaigns'

    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), nullable=False, default=CampaignStatus.CREATED)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'), nullable=True)
    status_message = db.Column(db.Text, nullable=True)
    status_error = db.Column(db.Text, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    failed_at = db.Column(db.DateTime, nullable=True)
    searchUrl = db.Column(db.Text, nullable=False)
    count = db.Column(db.Integer, nullable=False)
    excludeGuessedEmails = db.Column(db.Boolean, nullable=False, default=True)
    excludeNoEmails = db.Column(db.Boolean, nullable=False, default=True)
    getEmails = db.Column(db.Boolean, nullable=False, default=True)

    # Define valid status transitions
    VALID_TRANSITIONS = {
        CampaignStatus.CREATED: [CampaignStatus.FETCHING_LEADS],
        CampaignStatus.FETCHING_LEADS: [CampaignStatus.VERIFYING_EMAILS, CampaignStatus.FAILED],
        CampaignStatus.VERIFYING_EMAILS: [CampaignStatus.ENRICHING_LEADS, CampaignStatus.FAILED],
        CampaignStatus.ENRICHING_LEADS: [CampaignStatus.GENERATING_EMAILS, CampaignStatus.FAILED],
        CampaignStatus.GENERATING_EMAILS: [CampaignStatus.COMPLETED, CampaignStatus.FAILED],
        CampaignStatus.COMPLETED: [],
        CampaignStatus.FAILED: []
    }

    # Define job type to status mapping
    JOB_STATUS_MAP = {
        'FETCH_LEADS': {
            'COMPLETED': CampaignStatus.VERIFYING_EMAILS,
            'FAILED': CampaignStatus.FAILED
        },
        'VERIFY_EMAILS': {
            'COMPLETED': CampaignStatus.ENRICHING_LEADS,
            'FAILED': CampaignStatus.FAILED
        },
        'ENRICH_LEADS': {
            'COMPLETED': CampaignStatus.GENERATING_EMAILS,
            'FAILED': CampaignStatus.FAILED
        },
        'GENERATE_EMAILS': {
            'COMPLETED': CampaignStatus.COMPLETED,
            'FAILED': CampaignStatus.FAILED
        }
    }

    def __init__(self, name=None, description=None, organization_id=None, id=None, created_at=None, status=None, 
                 status_message=None, status_error=None, searchUrl=None, count=None, excludeGuessedEmails=True, excludeNoEmails=True, getEmails=True):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.created_at = created_at or datetime.utcnow()
        self.organization_id = organization_id
        self.status = status or CampaignStatus.CREATED
        self.status_message = status_message
        self.status_error = status_error
        self.updated_at = datetime.utcnow()
        self.searchUrl = searchUrl
        self.count = count
        self.excludeGuessedEmails = excludeGuessedEmails
        self.excludeNoEmails = excludeNoEmails
        self.getEmails = getEmails

    def is_valid_transition(self, new_status: str) -> bool:
        """Check if status transition is valid."""
        logger.info(f"Checking status transition from {self.status} to {new_status}")
        
        if self.status not in self.VALID_TRANSITIONS:
            logger.error(f"Invalid current status: {self.status}")
            return False
            
        if new_status not in self.VALID_TRANSITIONS[self.status]:
            logger.error(f"Invalid transition from {self.status} to {new_status}")
            return False
        
        return True

    def update_status(self, status: CampaignStatus, error_message: str = None) -> None:
        """Update campaign status."""
        self.status = status
        if error_message:
            self.status_error = error_message
        self.updated_at = datetime.utcnow()
        db.session.commit()

    def to_dict(self) -> Dict[str, Any]:
        """Convert campaign to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'organization_id': self.organization_id,
            'searchUrl': self.searchUrl,
            'count': self.count,
            'excludeGuessedEmails': self.excludeGuessedEmails,
            'excludeNoEmails': self.excludeNoEmails,
            'getEmails': self.getEmails
        }

    def __repr__(self):
        return f'<Campaign {self.id} status={self.status}>'

    def handle_job_status_update(self, job_type, job_status, error=None):
        """Handle job status updates and update campaign status accordingly."""
        try:
            logger.info(f"Handling job status update: type={job_type}, status={job_status}")
            
            # Convert job type to uppercase for comparison
            job_type = job_type.upper()
            job_status = job_status.upper()
            
            # Validate job type
            if job_type not in Job.VALID_JOB_TYPES:
                error_message = JOB_ERRORS['INVALID_JOB_TYPE'].format(job_type=job_type)
                logger.error(error_message)
                self.update_status(
                    CampaignStatus.FAILED,
                    error_message=error_message
                )
                return
            
            # Handle failed jobs immediately
            if job_status == 'FAILED':
                error_message = f"Job {job_type} failed: {error}" if error else f"Job {job_type} failed"
                logger.error(error_message)
                self.update_status(
                    CampaignStatus.FAILED,
                    error_message=error_message
                )
                return

            # Validate job status
            if job_status not in Job.VALID_STATUSES:
                error_message = JOB_ERRORS['INVALID_STATUS'].format(status=job_status)
                logger.error(error_message)
                self.update_status(
                    CampaignStatus.FAILED,
                    error_message=error_message
                )
                return

            # Get all jobs for this campaign
            jobs = Job.query.filter_by(campaign_id=self.id).all()
            
            # If any job has failed, campaign should be marked as failed
            if any(job.status == 'FAILED' for job in jobs):
                error_message = "One or more jobs have failed"
                logger.error(error_message)
                self.update_status(
                    CampaignStatus.FAILED,
                    error_message=error_message
                )
                return

            # Check if all jobs are completed
            if job_status == 'COMPLETED' and all(job.status == 'COMPLETED' for job in jobs):
                logger.info("All jobs completed successfully")
                self.update_status(
                    CampaignStatus.COMPLETED,
                    message="All jobs completed successfully"
                )
                return

            # Get next status from job status map
            next_status = self.JOB_STATUS_MAP.get(job_type, {}).get(job_status)
            if not next_status:
                error_message = f"No next status defined for job type {job_type} with status {job_status}"
                logger.error(error_message)
                self.update_status(
                    CampaignStatus.FAILED,
                    error_message=error_message
                )
                return

            # Check if we're already in a terminal state
            if self.status in [CampaignStatus.COMPLETED, CampaignStatus.FAILED]:
                error_message = CAMPAIGN_ERRORS['INVALID_STATUS_TRANSITION'].format(
                    current_status=self.status,
                    new_status=next_status
                )
                logger.error(error_message)
                return

            # Validate and perform status transition
            if self.is_valid_transition(next_status):
                self.update_status(
                    next_status,
                    message=f"Successfully completed {job_type}"
                )
                logger.info(f"Successfully updated campaign status to {next_status}")
            else:
                error_message = CAMPAIGN_ERRORS['INVALID_STATUS_TRANSITION'].format(
                    current_status=self.status,
                    new_status=next_status
                )
                logger.error(error_message)
                self.update_status(
                    CampaignStatus.FAILED,
                    error_message=error_message
                )
        except Exception as e:
            error_message = f"Error handling job status update: {str(e)}"
            logger.error(error_message, exc_info=True)
            self.update_status(
                CampaignStatus.FAILED,
                error_message=error_message
            ) 