from sqlalchemy import Column, String, Text, DateTime, Integer, Enum, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from typing import Dict, Any, List

from app.core.database import Base
from app.models.campaign_status import CampaignStatus


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(Enum(CampaignStatus), default=CampaignStatus.CREATED, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    status_message = Column(Text, nullable=True)
    status_error = Column(Text, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    fileName = Column(String(255), nullable=False)
    totalRecords = Column(Integer, nullable=False)
    url = Column(Text, nullable=False)
    instantly_campaign_id = Column(String(64), nullable=True)

    # Relationship to jobs
    jobs = relationship("Job", back_populates="campaign")

    # Relationship to leads
    leads = relationship("Lead", back_populates="campaign")

    # Relationship to organization
    organization = relationship("Organization", back_populates="campaigns")

    # Define valid status transitions
    VALID_TRANSITIONS = {
        CampaignStatus.CREATED: [CampaignStatus.RUNNING, CampaignStatus.FAILED],
        CampaignStatus.RUNNING: [CampaignStatus.PAUSED, CampaignStatus.COMPLETED, CampaignStatus.FAILED],
        CampaignStatus.PAUSED: [CampaignStatus.RUNNING, CampaignStatus.FAILED],  # Can resume or fail
        CampaignStatus.COMPLETED: [],
        CampaignStatus.FAILED: []
    }

    def is_valid_transition(self, new_status: CampaignStatus) -> bool:
        """Check if status transition is valid."""
        return new_status in self.VALID_TRANSITIONS.get(self.status, [])

    def update_status(self, new_status: CampaignStatus, status_message: str = None, status_error: str = None) -> bool:
        """
        Update campaign status with validation.
        Returns True if update was successful, False if transition is invalid.
        """
        # Allow updating message or error even if status is unchanged
        if self.status == new_status:
            if status_message is not None:
                self.status_message = status_message
            if status_error is not None:
                self.status_error = status_error
            return True

        # Validate transition
        if not self.is_valid_transition(new_status):
            return False

        # Update status and related fields
        self.status = new_status
        if status_message is not None:
            self.status_message = status_message
        if status_error is not None:
            self.status_error = status_error

        # Set completion/failure timestamps
        now = datetime.utcnow()
        if new_status == CampaignStatus.COMPLETED:
            self.completed_at = now
        elif new_status == CampaignStatus.FAILED:
            self.failed_at = now

        return True

    def get_valid_transitions(self) -> List[CampaignStatus]:
        """Get list of valid status transitions from current status."""
        return self.VALID_TRANSITIONS.get(self.status, [])

    def pause(self, reason: str = None) -> bool:
        """
        Pause a running campaign.
        Returns True if pause was successful, False if transition is invalid.
        """
        if self.status != CampaignStatus.RUNNING:
            return False
        
        return self.update_status(
            CampaignStatus.PAUSED,
            status_message=f"Campaign paused: {reason}" if reason else "Campaign paused",
            status_error=reason if reason else None
        )

    def resume(self, message: str = None) -> bool:
        """
        Resume a paused campaign.
        Returns True if resume was successful, False if transition is invalid.
        """
        if self.status != CampaignStatus.PAUSED:
            return False
        
        return self.update_status(
            CampaignStatus.RUNNING,
            status_message=message or "Campaign resumed",
            status_error=None  # Clear any pause-related errors
        )

    def can_be_started(self) -> tuple[bool, str]:
        """
        Check if campaign can be started.
        Returns (can_start, reason).
        """
        if self.status == CampaignStatus.PAUSED:
            return False, "Cannot start paused campaign - resume it first"
        elif self.status == CampaignStatus.RUNNING:
            return False, "Campaign is already running"
        elif self.status == CampaignStatus.COMPLETED:
            return False, "Cannot start completed campaign"
        elif self.status == CampaignStatus.FAILED:
            return False, "Cannot start failed campaign"
        elif self.status == CampaignStatus.CREATED:
            return True, "Campaign can be started"
        else:
            return False, f"Unknown campaign status: {self.status}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert campaign to dictionary for serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status.value if self.status else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'organization_id': self.organization_id,
            'status_message': self.status_message or '',
            'status_error': self.status_error or '',
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'failed_at': self.failed_at.isoformat() if self.failed_at else None,
            'fileName': self.fileName,
            'totalRecords': self.totalRecords,
            'url': self.url,
            'instantly_campaign_id': self.instantly_campaign_id
        }

    def __repr__(self):
        return f'<Campaign {self.id} status={self.status.value if self.status else None}>' 