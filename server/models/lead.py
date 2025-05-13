from datetime import datetime
from typing import Dict, Any
import uuid
from server.config.database import db
from sqlalchemy.dialects.postgresql import JSON

class Lead(db.Model):
    """Lead model for storing lead information."""
    
    __tablename__ = 'leads'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = db.Column(db.String(36), db.ForeignKey('campaigns.id'), nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    email = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    company = db.Column(db.String(255))
    title = db.Column(db.String(255))
    linkedin_url = db.Column(db.String(255))
    source_url = db.Column(db.String(255))
    raw_data = db.Column(db.JSON)
    email_verification = db.Column(db.JSON, nullable=True)
    enrichment_results = db.Column(db.JSON, nullable=True)
    enrichment_job_id = db.Column(db.String(36), nullable=True)
    email_copy_gen_results = db.Column(db.JSON, nullable=True)
    instantly_lead_record = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert lead to dictionary."""
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