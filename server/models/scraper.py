from datetime import datetime
from server.config.database import db
from sqlalchemy.dialects.postgresql import JSONB

class Scraper(db.Model):
    """Model for web scrapers."""
    __tablename__ = 'scrapers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    url_pattern = db.Column(db.String(255), nullable=False)
    selectors = db.Column(JSONB, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Scraper {self.name}>'

    def to_dict(self):
        """Convert the model to a dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'url_pattern': self.url_pattern,
            'selectors': self.selectors,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 