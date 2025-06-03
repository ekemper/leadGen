from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from typing import Dict, Any
from app.core.database import Base

class Lead(Base):
    __tablename__ = 'leads'

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    campaign_id = Column(String(36), ForeignKey('campaigns.id'), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(255), index=True)
    phone = Column(String(50))
    company = Column(String(255))
    title = Column(String(255))
    linkedin_url = Column(String(255))
    source_url = Column(String(255))
    raw_data = Column(JSON)
    email_verification = Column(JSON, nullable=True)
    enrichment_results = Column(JSON, nullable=True)
    enrichment_job_id = Column(String(36), nullable=True)
    email_copy_gen_results = Column(JSON, nullable=True)
    instantly_lead_record = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationship to campaign
    campaign = relationship('Campaign', back_populates='leads')

    # Add unique constraint on email field (only for non-null emails)
    __table_args__ = (
        Index('idx_leads_email_unique', 'email', unique=True, postgresql_where="email IS NOT NULL"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone': self.phone,
            'company': self.company,
            'title': self.title,
            'linkedin_url': self.linkedin_url,
            'source_url': self.source_url,
            'raw_data': self.raw_data,
            'email_verification': self.email_verification,
            'enrichment_results': self.enrichment_results,
            'enrichment_job_id': self.enrichment_job_id,
            'email_copy_gen_results': self.email_copy_gen_results,
            'instantly_lead_record': self.instantly_lead_record,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<Lead {self.id}>' 