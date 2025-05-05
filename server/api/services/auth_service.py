import re
import bcrypt
import jwt
import uuid
from datetime import datetime, timedelta
from flask import current_app
from server.models import User
from server.config.database import db
from server.utils.logger import logger
from server.api.services.validation_service import ValidationService
from email_validator import validate_email, EmailNotValidError
from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden

class AuthService:
    """Service for handling authentication-related operations."""

    @staticmethod
    def validate_password(password: str) -> None:
        """
        Validate password strength.
        
        Args:
            password: The password to validate
            
        Raises:
            BadRequest: If the password doesn't meet requirements
        """
        if len(password) < 8:
            raise BadRequest("Password must be at least 8 characters long")
            
        if not re.search(r"[A-Za-z]", password):
            raise BadRequest("Password must contain at least one letter")
            
        if not re.search(r"\d", password):
            raise BadRequest("Password must contain at least one number")
            
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            raise BadRequest("Password must contain at least one special character")

    @staticmethod
    def validate_email_format(email: str) -> None:
        """
        Validate email format.
        
        Args:
            email: The email to validate
            
        Raises:
            BadRequest: If the email format is invalid
        """
        try:
            # Validate email format
            validation = validate_email(email, check_deliverability=False)
            email = validation.email
            
            # Check length
            if len(email) > 254:  # Maximum length for email addresses
                raise BadRequest("Email length exceeds maximum allowed")
                
        except EmailNotValidError as e:
            raise BadRequest("Invalid email format")

    @classmethod
    def signup(cls, email: str, password: str, confirm_password: str) -> dict:
        """
        Register a new user.
        
        Args:
            email: User's email
            password: User's password
            confirm_password: Password confirmation
            
        Returns:
            dict: Registration result
            
        Raises:
            BadRequest: For validation errors
        """
        # Validate passwords match
        if password != confirm_password:
            raise BadRequest("Passwords do not match")
            
        # Validate password strength
        cls.validate_password(password)
        
        # Validate email format
        cls.validate_email_format(email)
        
        # Check if user already exists
        if User.query.filter_by(email=email.lower()).first():
            raise BadRequest("Email already registered")
            
        # Create new user
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user = User(
            id=str(uuid.uuid4()),
            email=email.lower(),
            password=hashed
        )
        
        try:
            db.session.add(user)
            db.session.commit()
            return {'success': True, 'message': 'User registered successfully'}
        except Exception as e:
            db.session.rollback()
            raise BadRequest(f"Error creating user: {str(e)}")

    @classmethod
    def login(cls, email: str, password: str) -> dict:
        """
        Authenticate a user.
        
        Args:
            email: User's email
            password: User's password
            
        Returns:
            dict: Authentication result
            
        Raises:
            Unauthorized: For invalid credentials
            Forbidden: For locked accounts
        """
        user = User.query.filter_by(email=email.lower()).first()
        
        # Validate email format first
        try:
            cls.validate_email_format(email)
        except BadRequest as e:
            raise Unauthorized(str(e))
        
        if not user:
            raise Unauthorized("Invalid email or password")
            
        # Check if account is locked
        if user.failed_attempts >= 5 and user.last_failed_attempt:
            lockout_duration = timedelta(minutes=15)
            if datetime.utcnow() - user.last_failed_attempt < lockout_duration:
                raise Forbidden("Account is locked due to too many failed attempts")
            else:
                # Reset failed attempts after lockout period
                user.failed_attempts = 0
                user.last_failed_attempt = None
                db.session.commit()
        
        # Verify password
        if not bcrypt.checkpw(password.encode('utf-8'), user.password):
            user.failed_attempts += 1
            user.last_failed_attempt = datetime.utcnow()
            db.session.commit()
            raise Unauthorized("Invalid email or password")
            
        # Reset failed attempts on successful login
        user.failed_attempts = 0
        user.last_failed_attempt = None
        db.session.commit()
        
        # Generate token
        token = jwt.encode(
            {
                'user_id': user.id,
                'exp': datetime.utcnow() + timedelta(days=1)
            },
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )
        
        return {
            'success': True,
            'message': 'Login successful',
            'token': token
        } 