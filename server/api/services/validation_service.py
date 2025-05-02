from email_validator import validate_email, EmailNotValidError
import re
from server.models import User
from typing import Dict, Union

class ValidationService:
    @staticmethod
    def validate_password(password: str) -> Dict[str, Union[bool, str]]:
        """Validate password complexity."""
        if not password or len(password) < 8:
            return {
                'success': False,
                'message': "Password must be at least 8 characters long"
            }
        if not re.search(r"[A-Za-z]", password):
            return {
                'success': False,
                'message': "Password must contain at least one letter"
            }
        if not re.search(r"\d", password):
            return {
                'success': False,
                'message': "Password must contain at least one number"
            }
        if not re.search(r"[@$!%*#?&]", password):
            return {
                'success': False,
                'message': "Password must contain at least one special character"
            }
        return {
            'success': True,
            'message': None
        }

    @staticmethod
    def validate_input_length(email: str, password: str) -> Dict[str, Union[bool, str]]:
        """Validate input lengths."""
        if len(email) > 254:  # RFC 5321
            return {
                'success': False,
                'message': "Email length exceeds maximum allowed"
            }
        if len(password) > 72:  # bcrypt limitation
            return {
                'success': False,
                'message': "Password length exceeds maximum allowed"
            }
        return {
            'success': True,
            'message': None
        }

    @staticmethod
    def validate_login_input(email: str, password: str) -> Dict[str, Union[bool, str]]:
        """Validate login input fields."""
        if not email:
            return {
                'success': False,
                'message': "Email is required"
            }
        if not password:
            return {
                'success': False,
                'message': "Password is required"
            }

        try:
            # Validate email
            validation_kwargs = {
                'check_deliverability': False,  # Disable deliverability check for testing
            }
            validate_email(email, **validation_kwargs)
        except EmailNotValidError:
            return {
                'success': False,
                'message': "Invalid email format"
            }

        return {
            'success': True,
            'message': None
        }

    @staticmethod
    def validate_signup_input(email: str, password: str, confirm_password: str) -> Dict[str, Union[bool, str]]:
        """Validate signup input fields."""
        if not email or not password or not confirm_password:
            return {
                'success': False,
                'message': "All fields are required"
            }

        # Validate input lengths first
        length_validation = ValidationService.validate_input_length(email, password)
        if not length_validation['success']:
            return length_validation

        try:
            # Validate email format
            validation_kwargs = {
                'check_deliverability': False,  # Disable deliverability check for testing
            }
            validation = validate_email(email, **validation_kwargs)
            email = validation.normalized

            # Check if email already exists (case-insensitive)
            existing_user = User.query.filter(User.email.ilike(email)).first()
            if existing_user:
                return {
                    'success': False,
                    'message': "Email already registered"
                }

        except EmailNotValidError:
            return {
                'success': False,
                'message': "Invalid email format"
            }

        # Check password match
        if password != confirm_password:
            return {
                'success': False,
                'message': "Passwords do not match"
            }

        # Validate password complexity
        password_validation = ValidationService.validate_password(password)
        if not password_validation['success']:
            return password_validation

        return {
            'success': True,
            'message': None
        } 