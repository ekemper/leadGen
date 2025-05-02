from datetime import datetime
import uuid
from typing import Dict, Any

class Lead:
    def __init__(self, **kwargs):
        self.guid = kwargs.get('guid', str(uuid.uuid4()))
        self.id = self.guid  # For backward compatibility
        self.name = kwargs.get('name', '')
        self.email = kwargs.get('email', '')
        self.company = kwargs.get('company', '')
        self.phone = kwargs.get('phone', '')
        self.status = kwargs.get('status', 'new')
        self.source = kwargs.get('source', 'apollo')
        self.notes = kwargs.get('notes', '')
        self.created_at = kwargs.get('created_at', datetime.utcnow().isoformat())
        self.updated_at = self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            'guid': self.guid,
            'id': self.id,  # For backward compatibility
            'name': self.name,
            'email': self.email,
            'company': self.company,
            'phone': self.phone,
            'status': self.status,
            'source': self.source,
            'notes': self.notes,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Lead':
        lead = cls(**data)
        lead.guid = data.get('guid', str(uuid.uuid4()))
        lead.id = lead.guid  # For backward compatibility
        lead.created_at = data.get('created_at', datetime.utcnow().isoformat())
        lead.updated_at = data.get('updated_at', datetime.utcnow().isoformat())
        return lead 