from datetime import datetime
import uuid
import json
import logging
from server.config.database import db
from sqlalchemy.dialects.postgresql import JSON
from server.utils.logging_config import server_logger
from server.utils.error_messages import JOB_ERRORS
from typing import Optional, Dict, Any
from server.models.job_status import JobStatus

logger = logging.getLogger(__name__)

class Job(db.Model):
    __tablename__ = 'jobs'

    id = db.Column(db.String(36), primary_key=True)
    campaign_id = db.Column(db.String(36), db.ForeignKey('campaigns.id'), nullable=False)
    job_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False, default=JobStatus.PENDING)
    parameters = db.Column(db.JSON)
    result = db.Column(db.JSON)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    # Define valid job statuses using the enum
    VALID_STATUSES = [status.value for status in JobStatus]

    # Define valid job types and their required result schemas
    VALID_JOB_TYPES = {
        'FETCH_LEADS': {
            'required_fields': ['leads', 'total_count'],
            'result_schema': {
                'leads': list,
                'total_count': int
            }
        },
        'VERIFY_EMAILS': {
            'required_fields': ['verified_count', 'invalid_count'],
            'result_schema': {
                'verified_count': int,
                'invalid_count': int
            }
        },
        'ENRICH_LEADS': {
            'required_fields': ['enriched_count', 'failed_count'],
            'result_schema': {
                'enriched_count': int,
                'failed_count': int
            }
        },
        'GENERATE_EMAILS': {
            'required_fields': ['generated_count', 'failed_count'],
            'result_schema': {
                'generated_count': int,
                'failed_count': int
            }
        }
    }

    campaign = db.relationship('Campaign', backref=db.backref('jobs', lazy=True))

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary."""
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'job_type': self.job_type,
            'status': self.status,
            'parameters': self.parameters,
            'result': self.result,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

    def __repr__(self):
        return f'<Job {self.id} type={self.job_type} status={self.status}>'

    @classmethod
    def validate_result(cls, job_type: str, result: Any) -> None:
        """Validate job result based on job type."""
        try:
            # First validate that result is not None
            if result is None:
                error_msg = JOB_ERRORS['RESULT_CORRUPTED']
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Validate result is a dictionary
            if not isinstance(result, dict):
                error_msg = JOB_ERRORS['RESULT_NOT_DICT']
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Validate required fields based on job type
            if job_type == 'FETCH_LEADS':
                if 'leads' not in result:
                    error_msg = JOB_ERRORS['MISSING_REQUIRED_FIELD'].format(field='leads')
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                if not isinstance(result['leads'], list):
                    error_msg = JOB_ERRORS['INVALID_FIELD_TYPE'].format(field='leads', expected='list')
                    logger.error(error_msg)
                    raise ValueError(error_msg)

            elif job_type == 'VERIFY_EMAILS':
                if 'verified_emails' not in result:
                    error_msg = JOB_ERRORS['MISSING_REQUIRED_FIELD'].format(field='verified_emails')
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                if not isinstance(result['verified_emails'], list):
                    error_msg = JOB_ERRORS['INVALID_FIELD_TYPE'].format(field='verified_emails', expected='list')
                    logger.error(error_msg)
                    raise ValueError(error_msg)

            elif job_type == 'ENRICH_LEADS':
                if 'enriched_leads' not in result:
                    error_msg = JOB_ERRORS['MISSING_REQUIRED_FIELD'].format(field='enriched_leads')
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                if not isinstance(result['enriched_leads'], list):
                    error_msg = JOB_ERRORS['INVALID_FIELD_TYPE'].format(field='enriched_leads', expected='list')
                    logger.error(error_msg)
                    raise ValueError(error_msg)

            elif job_type == 'GENERATE_EMAILS':
                if 'generated_emails' not in result:
                    error_msg = JOB_ERRORS['MISSING_REQUIRED_FIELD'].format(field='generated_emails')
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                if not isinstance(result['generated_emails'], list):
                    error_msg = JOB_ERRORS['INVALID_FIELD_TYPE'].format(field='generated_emails', expected='list')
                    logger.error(error_msg)
                    raise ValueError(error_msg)

        except ValueError:
            raise
        except Exception as e:
            error_msg = JOB_ERRORS['INVALID_RESULT_FORMAT'].format(error=str(e))
            logger.error(error_msg)
            raise ValueError(error_msg)

    def update_status(self, status: JobStatus, error_message: str = None) -> None:
        """Update job status."""
        if not isinstance(status, JobStatus):
            raise ValueError(f"Status must be a JobStatus enum value, got {type(status)}")
            
        self.status = status.value
        if error_message:
            self.error_message = error_message
        self.updated_at = datetime.utcnow()
        
        if status == JobStatus.RUNNING and not self.started_at:
            self.started_at = datetime.utcnow()
        elif status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            self.completed_at = datetime.utcnow()
            
        db.session.commit()

    @classmethod
    def create(cls, campaign_id: str, job_type: str, parameters: Dict[str, Any] = None) -> 'Job':
        """Create a new job."""
        job = cls(
            id=str(uuid.uuid4()),
            campaign_id=campaign_id,
            job_type=job_type,
            status=JobStatus.PENDING.value,
            parameters=parameters,
            created_at=datetime.utcnow()
        )
        db.session.add(job)
        return job 