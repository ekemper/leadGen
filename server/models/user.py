from datetime import datetime
import bcrypt
import uuid
from server.config.database import db

class User(db.Model):
    """User model for authentication."""
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False)
    password = db.Column(db.LargeBinary, nullable=False)
    failed_attempts = db.Column(db.Integer, default=0)
    last_failed_attempt = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, email: str, password: bytes, id: str = None, failed_attempts: int = 0):
        """
        Initialize a new user.
        
        Args:
            email: User's email address
            password: Hashed password
            id: User's UUID (generated if not provided)
            failed_attempts: Number of failed login attempts
        """
        self.id = id or str(uuid.uuid4())
        self.email = email.lower()
        self.password = password
        self.failed_attempts = failed_attempts
        self.last_failed_attempt = None

    def check_password(self, password):
        """Check if the provided password matches the stored hash."""
        if isinstance(self.password, str):
            stored_password = self.password.encode('utf-8')
        else:
            stored_password = self.password
        return bcrypt.checkpw(password.encode('utf-8'), stored_password)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def __repr__(self):
        return f'<User {self.email}>' 