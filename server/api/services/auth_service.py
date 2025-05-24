import re
import bcrypt
import jwt
import uuid
from datetime import datetime, timedelta
from flask import current_app
from server.models import User
from server.config.database import db
from server.utils.logging_config import app_logger
from server.api.services.validation_service import ValidationService
from email_validator import validate_email, EmailNotValidError
from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden
from typing import Dict, Any, Optional
from server.api.schemas import UserSchema, LoginSchema, TokenSchema

class AuthService:
    """Service for handling authentication-related operations."""

    def __init__(self):
        self._ensure_transaction()

    def _ensure_transaction(self):
        """Ensure we have an active transaction."""
        if not db.session.is_active:
            db.session.begin()

    @staticmethod
    def hash_password(password: str) -> bytes:
        """
        Hash a password using bcrypt.
        
        Args:
            password: The plain text password to hash
            
        Returns:
            bytes: The hashed password
        """
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    @staticmethod
    def verify_password(password: str, hashed_password: bytes) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            password: The plain text password to verify
            hashed_password: The hashed password to check against
            
        Returns:
            bool: True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                hashed_password if isinstance(hashed_password, bytes) else hashed_password.encode('utf-8')
            )
        except Exception as e:
            app_logger.error(f"Error verifying password: {str(e)}")
            return False

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

    WHITELISTED_EMAILS = {
        "ethan@smartscalingai.com",
        "ek@alienunderpants.io",
        "test@domain.com",
        "test@example.com",  # added for automated tests
    }

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
        # Whitelist check – allow explicitly listed emails OR any from the special testing domain
        if email.lower() not in cls.WHITELISTED_EMAILS and not email.lower().endswith("@hellacooltestingdomain.pizza"):
            app_logger.warning(
                "Signup failed: email not whitelisted",
                extra={
                    'email': email,
                    'action': 'signup_failed',
                    'reason': 'email_not_whitelisted'
                }
            )
            raise Forbidden("This email is not allowed to sign up.")
        
        # Log signup attempt
        app_logger.info(
            "Signup attempt",
            extra={
                'email': email,
                'action': 'signup_attempt'
            }
        )
        
        # Validate passwords match
        if password != confirm_password:
            app_logger.warning(
                "Signup failed: passwords do not match",
                extra={
                    'email': email,
                    'action': 'signup_failed',
                    'reason': 'password_mismatch'
                }
            )
            raise BadRequest("Passwords do not match")
            
        # Validate password strength
        try:
            cls.validate_password(password)
        except BadRequest as e:
            app_logger.warning(
                "Signup failed: invalid password",
                extra={
                    'email': email,
                    'action': 'signup_failed',
                    'reason': 'invalid_password',
                    'error': str(e)
                }
            )
            raise
            
        # Validate email format
        try:
            cls.validate_email_format(email)
        except BadRequest as e:
            app_logger.warning(
                "Signup failed: invalid email",
                extra={
                    'email': email,
                    'action': 'signup_failed',
                    'reason': 'invalid_email',
                    'error': str(e)
                }
            )
            raise
        
        # Check if user already exists
        if User.query.filter_by(email=email.lower()).first():
            app_logger.warning(
                "Signup failed: email already registered",
                extra={
                    'email': email,
                    'action': 'signup_failed',
                    'reason': 'email_exists'
                }
            )
            raise BadRequest("Email already registered")
            
        # Create new user
        hashed_password = cls.hash_password(password)
        user = User(
            id=str(uuid.uuid4()),
            email=email.lower(),
            password=hashed_password
        )
        
        try:
            db.session.add(user)
            db.session.commit()
            
            # Log successful registration
            app_logger.info(
                "User registered successfully",
                extra={
                    'user_id': user.id,
                    'email': email,
                    'action': 'signup_success'
                }
            )
            
            return {'success': True, 'message': 'User registered successfully'}
        except Exception as e:
            db.session.rollback()
            app_logger.error(
                "Error creating user",
                extra={
                    'email': email,
                    'action': 'signup_failed',
                    'reason': 'database_error',
                    'error': str(e)
                }
            )
            raise BadRequest(f"Error creating user: {str(e)}")

    def login(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Authenticate a user and return a token."""
        # Whitelist check – same rule as signup
        email = data.get('email', '').lower()
        if email not in self.WHITELISTED_EMAILS and not email.endswith("@hellacooltestingdomain.pizza"):
            app_logger.warning(
                "Login failed: email not whitelisted",
                extra={
                    'email': email,
                    'action': 'login_failed',
                    'reason': 'email_not_whitelisted'
                }
            )
            raise Forbidden("This email is not allowed to log in.")
        
        try:
            # Validate input data
            errors = LoginSchema().validate(data)
            if errors:
                raise BadRequest(f"Invalid login data: {errors}")
                
            user = User.query.filter_by(email=email).first()
            if not user or not user.check_password(data['password']):
                raise Unauthorized("Invalid email or password")
            
            # Generate token
            token_data = {
                'user_id': user.id,
                'email': user.email,
                'exp': datetime.utcnow() + timedelta(days=1)
            }
            token = jwt.encode(
                token_data,
                current_app.config['SECRET_KEY'],
                algorithm='HS256'
            )
            
            # Log token generation
            app_logger.info(
                "Token generated",
                extra={
                    'user_id': user.id,
                    'email': user.email,
                    'action': 'token_generated'
                }
            )
            
            # Prepare response
            response_data = {
                'token': token,
                'user': user.to_dict()
            }
            
            return response_data
        except Exception as e:
            app_logger.error(f'Error during login: {str(e)}', exc_info=True)
            db.session.rollback()
            raise

    def register(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new user."""
        try:
            # Validate input data
            errors = UserSchema().validate(data)
            if errors:
                raise ValueError(f"Invalid user data: {errors}")
                
            # Check if user already exists
            if User.query.filter_by(email=data['email']).first():
                raise ValueError("User with this email already exists")
            
            # Create new user
            user = User(
                email=data['email'],
                name=data['name']
            )
            user.set_password(data['password'])
            
            db.session.add(user)
            db.session.commit()
            
            # Generate token
            token_data = {
                'user_id': user.id,
                'email': user.email,
                'exp': datetime.utcnow() + timedelta(days=1)
            }
            token = jwt.encode(
                token_data,
                current_app.config['SECRET_KEY'],
                algorithm='HS256'
            )
            
            # Prepare response
            response_data = {
                'token': token,
                'user': user.to_dict()
            }
            
            # Validate response data
            errors = TokenSchema().validate(response_data)
            if errors:
                raise ValueError(f"Invalid token data: {errors}")
                
            return response_data
        except Exception as e:
            app_logger.error(f'Error during registration: {str(e)}', exc_info=True)
            db.session.rollback()
            raise

    def get_current_user(self, token: str) -> Dict[str, Any]:
        """Get the current user from a token."""
        try:
            # Verify token
            try:
                payload = jwt.decode(
                    token,
                    current_app.config['SECRET_KEY'],
                    algorithms=['HS256']
                )
            except jwt.ExpiredSignatureError:
                raise Unauthorized("Token has expired")
            except jwt.InvalidTokenError:
                raise Unauthorized("Invalid token")
            
            user = User.query.get(payload['user_id'])
            if not user:
                raise Unauthorized("User not found")
            
            user_dict = user.to_dict()
            # Validate user data
            errors = UserSchema().validate(user_dict)
            if errors:
                raise ValueError(f"Invalid user data: {errors}")
            
            return user_dict
        except Exception as e:
            app_logger.error(f'Error getting current user: {str(e)}', exc_info=True)
            db.session.rollback()
            raise

    def update_user(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a user's information."""
        try:
            app_logger.info(f'Updating user {user_id}')
            self._ensure_transaction()
            
            user = User.query.get(user_id)
            if not user:
                app_logger.warning(f'User {user_id} not found')
                return None
            
            # Validate input data
            errors = UserSchema().validate(data)
            if errors:
                raise ValueError(f"Invalid user data: {errors}")
            
            # Update user fields
            for key, value in data.items():
                if key == 'password':
                    user.set_password(value)
                elif hasattr(user, key):
                    setattr(user, key, value)
            
            db.session.commit()
            
            user_dict = user.to_dict()
            # Validate output data
            errors = UserSchema().validate(user_dict)
            if errors:
                raise ValueError(f"Invalid user data: {errors}")
            
            return user_dict
        except Exception as e:
            app_logger.error(f'Error updating user: {str(e)}', exc_info=True)
            db.session.rollback()
            raise 