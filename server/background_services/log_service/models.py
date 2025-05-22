from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Optional

@dataclass
class LogEntry:
    timestamp: datetime
    source: str  # docker/process/application
    stream: str  # stdout/stderr
    content: str
    metadata: Dict
    context: Dict
    level: str = "INFO"
    service_name: Optional[str] = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

    def to_model_context(self) -> dict:
        """Convert log entry to model-friendly format"""
        return {
            'time': self.timestamp.isoformat(),
            'source': self.source,
            'content': self.content,
            'level': self.level,
            'service': self.service_name,
            'context': {
                **self.context,
                **self.metadata
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'LogEntry':
        if isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data) 