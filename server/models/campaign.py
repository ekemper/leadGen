from datetime import datetime
import uuid
from server.config.database import db

class Campaign(db.Model):
    __tablename__ = 'campaigns'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'), nullable=True)

    def __init__(self, id=None, created_at=None, organization_id=None):
        self.id = id or str(uuid.uuid4())
        self.created_at = created_at or datetime.utcnow()
        self.organization_id = organization_id

    def to_dict(self):
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat(),
            'organization_id': self.organization_id
        }

    def __repr__(self):
        return f'<Campaign {self.id}>' 