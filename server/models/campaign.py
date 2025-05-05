from datetime import datetime
import uuid
from server.config.database import db
import logging

logger = logging.getLogger(__name__)

class Campaign(db.Model):
    __tablename__ = 'campaigns'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'), nullable=False)
    status = db.Column(db.String(50), default='created', nullable=False)

    def __init__(self, name=None, description=None, organization_id=None, id=None, created_at=None, status=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.created_at = created_at or datetime.utcnow()
        self.organization_id = organization_id
        self.status = status or 'created'

    def to_dict(self):
        try:
            return {
                'id': self.id,
                'name': self.name,
                'description': self.description,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'organization_id': self.organization_id,
                'status': self.status
            }
        except Exception as e:
            logger.error(f'Error converting campaign {self.id} to dict: {str(e)}')
            raise

    def __repr__(self):
        return f'<Campaign {self.id}>' 