from datetime import datetime
from typing import Dict, Any
import uuid
from server.config.database import db

class User(db.Model):
    """User model for storing user information."""
    
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    # Store password as bytes for bcrypt compatibility
    password = db.Column(db.LargeBinary, nullable=False)
    failed_attempts = db.Column(db.Integer, default=0)
    last_failed_attempt = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, email: str, password: bytes, id: str = None, failed_attempts: int = 0):
        """
        Initialize a new user.
        Args:
            email: User's email address
            password: Hashed password (bytes)
            id: User's UUID (generated if not provided)
            failed_attempts: Number of failed login attempts
        """
        self.id = id or str(uuid.uuid4())
        self.email = email.lower()
        self.name = ""  # Assuming name is not provided in the constructor
        self.password = password  # Should be bytes
        self.failed_attempts = failed_attempts
        self.last_failed_attempt = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary."""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def set_password(self, password: str) -> None:
        """Set user password."""
        from server.api.services.auth_service import AuthService
        self.password = AuthService.hash_password(password)

    def check_password(self, password: str) -> bool:
        """Check if password matches."""
        from server.api.services.auth_service import AuthService
        return AuthService.verify_password(password, self.password)

    def __repr__(self):
        return f'<User {self.email}>' 