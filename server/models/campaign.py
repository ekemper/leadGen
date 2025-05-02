from datetime import datetime
import uuid
from config.database import db

class Campaign(db.Model):
    __tablename__ = 'campaigns'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __init__(self, id=None, created_at=None):
        self.id = id or str(uuid.uuid4())
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self):
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self):
        return f'<Campaign {self.id}>' 