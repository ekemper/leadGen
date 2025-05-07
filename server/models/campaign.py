from datetime import datetime
import uuid
import logging
from server.config.database import db
from server.utils.logging_config import server_logger, combined_logger
from sqlalchemy.dialects.postgresql import JSON
from enum import Enum
from typing import Dict, Any, Optional
from server.models.campaign_status import CampaignStatus

logger = logging.getLogger(__name__)

class Campaign(db.Model):
    __tablename__ = 'campaigns'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'), nullable=True)
    status = db.Column(db.String(50), default=CampaignStatus.CREATED, nullable=False)
    status_message = db.Column(db.Text, nullable=True)
    status_error = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Define valid status transitions
    VALID_TRANSITIONS = {
        CampaignStatus.CREATED: [CampaignStatus.FETCHING_LEADS, CampaignStatus.FAILED],
        CampaignStatus.FETCHING_LEADS: [CampaignStatus.LEADS_FETCHED, CampaignStatus.FAILED],
        CampaignStatus.LEADS_FETCHED: [CampaignStatus.ENRICHING, CampaignStatus.FAILED],
        CampaignStatus.ENRICHING: [CampaignStatus.ENRICHED, CampaignStatus.FAILED],
        CampaignStatus.ENRICHED: [CampaignStatus.VERIFYING_EMAILS, CampaignStatus.FAILED],
        CampaignStatus.VERIFYING_EMAILS: [CampaignStatus.EMAILS_VERIFIED, CampaignStatus.FAILED],
        CampaignStatus.EMAILS_VERIFIED: [CampaignStatus.GENERATING_EMAILS, CampaignStatus.FAILED],
        CampaignStatus.GENERATING_EMAILS: [CampaignStatus.COMPLETED, CampaignStatus.FAILED],
        CampaignStatus.FAILED: [CampaignStatus.CREATED],  # Allow restart from failed state
        CampaignStatus.COMPLETED: []  # Terminal state
    }

    def __init__(self, name=None, description=None, organization_id=None, id=None, created_at=None, status=None, 
                 status_message=None, status_error=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.created_at = created_at or datetime.utcnow()
        self.organization_id = organization_id
        self.status = status or CampaignStatus.CREATED
        self.status_message = status_message
        self.status_error = status_error

    def is_valid_transition(self, new_status: CampaignStatus) -> bool:
        """
        Check if the status transition is valid.
        
        Args:
            new_status: The new status to transition to
            
        Returns:
            bool: True if the transition is valid, False otherwise
        """
        current_status = CampaignStatus(self.status) if isinstance(self.status, str) else self.status
        return new_status in self.VALID_TRANSITIONS.get(current_status, [])

    def update_status(self, status: CampaignStatus, message: Optional[str] = None, error: Optional[str] = None) -> None:
        """
        Update the campaign status and related fields with validation.
        
        Args:
            status: The new status from CampaignStatus enum
            message: Optional status message
            error: Optional error message
            
        Raises:
            ValueError: If the status transition is invalid
        """
        try:
            # Lock the row for update to prevent race conditions
            campaign = db.session.query(Campaign).with_lockmode('update').get(self.id)
            if not campaign:
                raise ValueError(f"Campaign {self.id} not found")

            # Validate status transition
            if not self.is_valid_transition(status):
                current_status = CampaignStatus(self.status) if isinstance(self.status, str) else self.status
                raise ValueError(
                    f"Invalid status transition from {current_status} to {status}. "
                    f"Valid transitions are: {self.VALID_TRANSITIONS.get(current_status, [])}"
                )

            # Store previous status for potential rollback
            previous_status = self.status
            previous_message = self.status_message
            previous_error = self.status_error

            try:
                self.status = status
                self.status_message = message
                self.status_error = error
                db.session.commit()

                server_logger.info(
                    f"Campaign {self.id} status updated from {previous_status} to {status}",
                    extra={
                        'component': 'server',
                        'campaign_id': self.id,
                        'previous_status': previous_status,
                        'new_status': status,
                        'message': message,
                        'error': error
                    }
                )
                combined_logger.info(
                    f"Campaign {self.id} status updated from {previous_status} to {status}",
                    extra={
                        'component': 'server',
                        'campaign_id': self.id,
                        'previous_status': previous_status,
                        'new_status': status,
                        'message': message,
                        'error': error
                    }
                )
            except Exception as e:
                # Rollback status change on error
                self.status = previous_status
                self.status_message = previous_message
                self.status_error = previous_error
                db.session.rollback()
                raise

        except Exception as e:
            server_logger.error(
                f"Error updating campaign status: {str(e)}",
                extra={
                    'component': 'server',
                    'campaign_id': self.id,
                    'error': str(e)
                }
            )
            combined_logger.error(
                f"Error updating campaign status: {str(e)}",
                extra={
                    'component': 'server',
                    'campaign_id': self.id,
                    'error': str(e)
                }
            )
            db.session.rollback()
            raise

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the campaign to a dictionary.
        
        Returns:
            Dict[str, Any]: The campaign as a dictionary
        """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'organization_id': self.organization_id,
            'status': self.status,
            'status_message': self.status_message,
            'status_error': self.status_error,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self) -> str:
        return f"<Campaign {self.id}: {self.name}>" 