import bcrypt
import jwt
import uuid
from datetime import datetime, timedelta
from flask import current_app
from models import User, db
from utils.logger import logger
from .validation_service import ValidationService

class AuthService:
    @staticmethod
    def signup(email: str, password: str, confirm_password: str) -> dict:
        """
        Handle user registration
        """
        try:
            # Validate input
            validation_result = ValidationService.validate_signup_input(email, password, confirm_password)
            if not validation_result['success']:
                return validation_result

            # Hash password
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

            # Create new user
            new_user = User(
                id=str(uuid.uuid4()),
                email=email,
                password=hashed_password,
                failed_attempts=0
            )

            # Add user to database
            db.session.add(new_user)
            db.session.commit()

            return {
                'success': True,
                'message': 'User registered successfully'
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during signup: {str(e)}")
            return {
                'success': False,
                'message': 'An error occurred during registration'
            }

    @staticmethod
    def login(email: str, password: str) -> dict:
        """
        Handle user login
        """
        try:
            # Validate input
            validation_result = ValidationService.validate_login_input(email, password)
            if not validation_result['success']:
                return {
                    'success': False,
                    'message': validation_result['message'],
                    'status_code': 400
                }

            # Get user from database
            user = User.query.filter_by(email=email).first()
            if not user:
                return {
                    'success': False,
                    'message': 'Invalid email or password',
                    'status_code': 401
                }

            # Check if account is locked
            if user.failed_attempts >= 5:
                return {
                    'success': False,
                    'message': 'Account is locked due to too many failed attempts',
                    'status_code': 403
                }

            # Verify password
            if not bcrypt.checkpw(password.encode('utf-8'), user.password):
                user.failed_attempts += 1
                db.session.commit()
                return {
                    'success': False,
                    'message': 'Invalid email or password',
                    'status_code': 401
                }

            # Reset failed attempts on successful login
            user.failed_attempts = 0
            db.session.commit()

            # Generate JWT token
            token = jwt.encode(
                {
                    'user_id': user.id,
                    'email': user.email,
                    'exp': datetime.utcnow() + timedelta(days=1)
                },
                current_app.config['SECRET_KEY'],
                algorithm='HS256'
            )

            return {
                'success': True,
                'message': 'Login successful',
                'token': token,
                'status_code': 200
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during login: {str(e)}")
            return {
                'success': False,
                'message': 'An error occurred during login',
                'status_code': 500
            } 