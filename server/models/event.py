from datetime import datetime
import uuid
from server.config.database import db
from sqlalchemy.dialects.postgresql import JSON

class Event(db.Model):
    __tablename__ = 'events'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source = db.Column(db.Enum('browser', 'api', 'database', name='event_source'), nullable=False)
    tag = db.Column(db.String(255), nullable=False)
    data = db.Column(JSON, nullable=False)
    type = db.Column(db.Enum('error', 'message', 'log', name='event_type'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __init__(self, source, tag, data, type, id=None, created_at=None, updated_at=None):
        self.id = id or str(uuid.uuid4())
        self.source = source
        self.tag = tag
        self.data = data
        self.type = type
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or self.created_at

    def to_dict(self):
        return {
            'id': self.id,
            'source': self.source,
            'tag': self.tag,
            'data': self.data,
            'type': self.type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<Event {self.id}>' 