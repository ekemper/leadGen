from datetime import datetime
import uuid
from server.config.database import db
from sqlalchemy.dialects.postgresql import JSON

class Lead(db.Model):
    __tablename__ = 'leads'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False, default='')
    email = db.Column(db.String(255), nullable=False, default='')
    company_name = db.Column(db.String(255), default='')
    phone = db.Column(db.String(50), default='')
    status = db.Column(db.String(50), default='new')
    source = db.Column(db.String(50), default='apollo')
    notes = db.Column(db.Text, default='')
    campaign_id = db.Column(db.String(36), db.ForeignKey('campaigns.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    raw_lead_data = db.Column(JSON, nullable=True)
    email_verification = db.Column(JSON, nullable=True)
    enrichment_results = db.Column(JSON, nullable=True)
    email_copy = db.Column(db.Text, nullable=True)

    campaign = db.relationship('Campaign', backref=db.backref('leads', lazy=True))

    def __init__(self, name='', email='', company_name='', phone='', status='new', source='apollo', notes='', campaign_id=None, id=None, created_at=None, updated_at=None, raw_lead_data=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.email = email
        self.company_name = company_name
        self.phone = phone
        self.status = status
        self.source = source
        self.notes = notes
        self.campaign_id = campaign_id
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or self.created_at
        self.raw_lead_data = raw_lead_data

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'company_name': self.company_name,
            'phone': self.phone,
            'status': self.status,
            'source': self.source,
            'notes': self.notes,
            'campaign_id': self.campaign_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'raw_lead_data': self.raw_lead_data,
            'email_verification': self.email_verification,
            'enrichment_results': self.enrichment_results,
            'email_copy': self.email_copy
        }

    def __repr__(self):
        return f'<Lead {self.id}>' 