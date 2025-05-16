from datetime import datetime
import uuid
import logging
from server.config.database import db
from server.utils.logging_config import app_logger
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
    fileName = db.Column(db.String(255), nullable=False)
    totalRecords = db.Column(db.Integer, nullable=False)
    url = db.Column(db.Text, nullable=False)
    instantly_campaign_id = db.Column(db.String(64), nullable=True)

    # Define valid status transitions (simplified)
    VALID_TRANSITIONS = {
        CampaignStatus.CREATED: [CampaignStatus.FETCHING_LEADS, CampaignStatus.FAILED],
        CampaignStatus.FETCHING_LEADS: [CampaignStatus.COMPLETED, CampaignStatus.FAILED],
        CampaignStatus.COMPLETED: [],
        CampaignStatus.FAILED: []
    }

    def __init__(self, name=None, description=None, organization_id=None, id=None, created_at=None, status=None, 
                 status_message=None, status_error=None, fileName=None, totalRecords=None, url=None, instantly_campaign_id=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.created_at = created_at or datetime.utcnow()
        self.organization_id = organization_id
        self.status = status or CampaignStatus.CREATED
        self.status_message = status_message
        self.status_error = status_error
        self.updated_at = datetime.utcnow()
        self.fileName = fileName
        self.totalRecords = totalRecords
        self.url = url
        self.instantly_campaign_id = instantly_campaign_id

    def is_valid_transition(self, new_status: str) -> bool:
        """Check if status transition is valid (simplified)."""
        return new_status in self.VALID_TRANSITIONS.get(self.status, [])

    def update_status(self, status: CampaignStatus, error_message: str = None) -> None:
        """Update campaign status (idempotent for same-status updates)."""
        if self.status == status:
            # Allow updating message or error even if status is unchanged
            if error_message:
                self.status_error = error_message
            self.updated_at = datetime.utcnow()
            db.session.commit()
            return
        if self.is_valid_transition(status):
            self.status = status
            if error_message:
                self.status_error = error_message
            self.updated_at = datetime.utcnow()
            db.session.commit()
        else:
            logger.error(f"Invalid status transition from {self.status} to {status}")

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
            'fileName': self.fileName,
            'totalRecords': self.totalRecords,
            'url': self.url,
            'status_message': self.status_message if self.status_message is not None else '',
            'status_error': self.status_error if self.status_error is not None else '',
            'instantly_campaign_id': self.instantly_campaign_id
        }

    def __repr__(self):
        return f'<Campaign {self.id} status={self.status}>' 