from flask import jsonify, request, g
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
from .services.lead_service import LeadService
import json
from flask import Blueprint
from services.apollo_service import ApolloService
from utils.middleware import log_function_call
from functools import wraps

# Initialize services
scraper_service = ScraperService()
apollo_service = ApolloService()
lead_service = LeadService()

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({
                'status': 'error',
                'message': 'Token is missing'
            }), 401
            
        try:
            # Decode the token
            data = jwt.decode(token, os.getenv('JWT_SECRET_KEY', 'your-secret-key'), algorithms=['HS256'])
            current_user = User.query.filter_by(id=data['user_id']).first()
            
            if not current_user:
                return jsonify({
                    'status': 'error',
                    'message': 'User not found'
                }), 401
                
            # Store the current user in the request context
            g.current_user = current_user
            
        except jwt.ExpiredSignatureError:
            return jsonify({
                'status': 'error',
                'message': 'Token has expired'
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid token'
            }), 401
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
            
        return f(*args, **kwargs)
    return decorated

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
    @token_required
    def root():
        """Root endpoint."""
        return jsonify({
            'message': 'Welcome to the Auth Template API',
            'version': '1.0.0'
        }), 200

    @api.route('/scrape', methods=['POST'])
    @token_required
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

    @api.route('/fetch_apollo_leads', methods=['POST'])
    @token_required
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

    @api.route('/leads', methods=['GET'])
    @token_required
    def get_leads():
        """Get all leads."""
        try:
            leads = lead_service.get_all_leads()
            return jsonify({
                'status': 'success',
                'data': [lead.to_dict() for lead in leads]
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @api.route('/leads', methods=['POST'])
    @token_required
    def create_lead():
        """Create a new lead."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'status': 'error',
                    'message': 'No data provided'
                }), 400

            lead, is_duplicate, reason = lead_service.create_lead(data)
            
            if is_duplicate:
                return jsonify({
                    'status': 'warning',
                    'message': reason,
                    'data': lead.to_dict()
                }), 200

            return jsonify({
                'status': 'success',
                'data': lead.to_dict()
            }), 201
        except ValueError as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 400
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @api.route('/leads/<lead_id>', methods=['GET'])
    @token_required
    def get_lead(lead_id):
        """Get a specific lead by ID."""
        try:
            lead = lead_service.get_lead(lead_id)
            if not lead:
                return jsonify({
                    'status': 'error',
                    'message': 'Lead not found'
                }), 404

            return jsonify({
                'status': 'success',
                'data': lead.to_dict()
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @api.route('/leads/<lead_id>', methods=['PUT'])
    @token_required
    def update_lead(lead_id):
        """Update a lead."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'status': 'error',
                    'message': 'No data provided'
                }), 400

            lead = lead_service.update_lead(lead_id, data)
            if not lead:
                return jsonify({
                    'status': 'error',
                    'message': 'Lead not found'
                }), 404

            return jsonify({
                'status': 'success',
                'data': lead.to_dict()
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @api.route('/leads/<lead_id>', methods=['DELETE'])
    @token_required
    def delete_lead(lead_id):
        """Delete a lead."""
        try:
            success = lead_service.delete_lead(lead_id)
            if not success:
                return jsonify({
                    'status': 'error',
                    'message': 'Lead not found'
                }), 404

            return jsonify({
                'status': 'success',
                'message': 'Lead deleted successfully'
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500 