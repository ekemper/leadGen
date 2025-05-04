from datetime import datetime
import uuid
from server.config.database import db

class Organization(db.Model):
    __tablename__ = 'organizations'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    campaigns = db.relationship('Campaign', backref='organization', lazy=True)

    def __init__(self, name, description=None, id=None, created_at=None, updated_at=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or self.created_at

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<Organization {self.id}>' 