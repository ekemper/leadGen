from flask import jsonify, request
from email_validator import validate_email, EmailNotValidError
from datetime import datetime, timedelta
import bcrypt
import jwt
import os
import re
import uuid
from models import User
from config.database import db
from utils.logger import logger
from werkzeug.exceptions import BadRequest
from .services.auth_service import AuthService
from .services.scraper_service import ScraperService
import json
from flask import Blueprint
from services.apollo_service import ApolloService
from utils.middleware import log_function_call

# Initialize services
scraper_service = ScraperService()
apollo_service = ApolloService()

def register_routes(api):
    """Register all routes with the provided blueprint."""
    
    @api.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        logger.debug('Health check endpoint called')
        return jsonify({
            'status': 'healthy',
            'message': 'API is running',
            'endpoint': '/api/health'
        }), 200

    @api.route('/auth/signup', methods=['POST'])
    def signup():
        """User registration endpoint."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Missing required fields'}), 400
        except BadRequest:
            return jsonify({'error': 'Invalid JSON payload'}), 400
        
        if not all(k in data for k in ['email', 'password', 'confirm_password']):
            return jsonify({'error': 'All fields are required'}), 400

        email = data['email'].lower().strip()
        password = data['password']
        confirm_password = data['confirm_password']

        result = AuthService.signup(email, password, confirm_password)
        if result['success']:
            return jsonify({'message': 'User registered successfully'}), 201
        else:
            return jsonify({'error': result['message']}), 400

    @api.route('/auth/login', methods=['POST'])
    def login():
        """User login endpoint."""
        try:
            # Set request timeout
            request.environ['REQUEST_TIMEOUT'] = 30

            # Get and validate input
            try:
                data = request.get_json()
            except Exception as e:
                logger.warning('Invalid JSON payload', extra={'error': str(e)})
                return jsonify({'error': 'Invalid JSON payload'}), 400

            if not data:
                logger.warning('Login attempt with no data provided')
                return jsonify({'error': 'No data provided'}), 400

            email = data.get('email', '').lower().strip()
            password = data.get('password', '')

            if not email or not password:
                logger.warning('Login attempt with missing email or password')
                return jsonify({'error': 'Missing email or password'}), 400

            result = AuthService.login(email, password)
            if result['success']:
                return jsonify({
                    'message': result['message'],
                    'token': result['token']
                }), result.get('status_code', 200)
            else:
                return jsonify({'error': result['message']}), result.get('status_code', 401)

        except Exception as e:
            logger.error('Login failed', extra={'error': str(e)}, exc_info=True)
            return jsonify({'error': 'An unexpected error occurred'}), 500

    @api.route('/')
    def root():
        """Root endpoint."""
        return jsonify({
            'message': 'Welcome to the Auth Template API',
            'version': '1.0.0'
        }), 200

    @api.route('/scrape', methods=['POST'])
    def scrape_url():
        # Validate request format
        if not request.is_json:
            return jsonify({
                "error": {
                    "code": "400",
                    "message": "Request must be JSON"
                }
            }), 400

        data = request.get_json()
        
        # Validate required fields
        if 'url' not in data:
            return jsonify({
                "error": {
                    "code": "400",
                    "message": "URL is required"
                }
            }), 400

        try:
            # Delegate to service
            result = scraper_service.scrape_and_save(data['url'])
            return jsonify(result)

        except ValueError as e:
            return jsonify({
                "error": {
                    "code": "400",
                    "message": str(e)
                }
            }), 400
        except Exception as e:
            return jsonify({
                "error": {
                    "code": "500",
                    "message": str(e)
                }
            }), 500

    @api.route('/fetch_apollo_leads', methods=['GET'])
    @log_function_call
    def fetch_apollo_leads():
        """
        Fetch leads from Apollo API and save to file.
        
        Request body:
        {
            "count": int,
            "excludeGuessedEmails": bool,
            "excludeNoEmails": bool,
            "getEmails": bool,
            "searchUrl": str
        }
        
        Returns:
            JSON response with operation status and message
        """
        try:
            # Get the request body
            params = request.get_json()
            
            # Validate required parameters
            required_params = ['count', 'excludeGuessedEmails', 'excludeNoEmails', 'getEmails', 'searchUrl']
            for param in required_params:
                if param not in params:
                    return jsonify({
                        "status": "error",
                        "message": f"Missing required parameter: {param}"
                    }), 400
            
            # Fetch leads using the Apollo service
            result = apollo_service.fetch_leads(params)
            
            # Return the operation status
            return jsonify(result)
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500 