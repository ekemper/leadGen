from flask import jsonify, request, g, current_app, abort
from email_validator import validate_email, EmailNotValidError
from datetime import datetime, timedelta
import bcrypt
import jwt
import os
import re
import uuid
from server.models import User
from server.config.database import db
from server.utils.logger import logger
from werkzeug.exceptions import BadRequest, Unauthorized, NotFound, InternalServerError
from server.api.services.auth_service import AuthService
from server.api.services.scraper_service import ScraperService
from server.api.services.lead_service import LeadService
import json
from flask import Blueprint
from server.background_services.apollo_service import ApolloService
from server.utils.middleware import log_function_call
from functools import wraps
from server.api.services.campaign_service import CampaignService
from server.api.services.organization_service import OrganizationService
from server.api.services.event_service import EventService

# Initialize services
scraper_service = ScraperService()
apollo_service = ApolloService()
lead_service = LeadService()
campaign_service = CampaignService()
organization_service = OrganizationService()
event_service = EventService()

# Create blueprint
api = Blueprint('api', __name__)

def token_required(f):
    """Decorator to protect routes with JWT authentication."""
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
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.filter_by(id=data['user_id']).first()
            
            if not current_user:
                return jsonify({
                    'status': 'error',
                    'message': 'User not found'
                }), 401
                
            # Add user to request context
            g.current_user = current_user
            return f(*args, **kwargs)
            
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

    @api.route('/')
    def root():
        """Root endpoint."""
        return jsonify({
            'status': 'success',
            'message': 'Welcome to the Auth Template API',
            'version': '1.0.0'
        }), 200

    @api.route('/auth/signup', methods=['POST'])
    def signup():
        """Handle user registration."""
        try:
            data = request.get_json()
            if not data:
                raise BadRequest("No input data provided")
            
            email = data.get('email')
            password = data.get('password')
            confirm_password = data.get('confirm_password')
            
            if not all([email, password, confirm_password]):
                raise BadRequest("All fields are required")
            
            result = AuthService.signup(email, password, confirm_password)
            return jsonify(result), 201
        
        except BadRequest as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 400
        
        except Exception as e:
            logger.error(f"Error during signup: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 400

    @api.route('/auth/login', methods=['POST'])
    def login():
        """Handle user login."""
        try:
            data = request.get_json()
            if not data:
                raise BadRequest("No input data provided")
            
            email = data.get('email')
            password = data.get('password')
            
            if not all([email, password]):
                raise BadRequest("Missing email or password")
            
            result = AuthService.login(email, password)
            return jsonify(result), 200
        
        except (BadRequest, Unauthorized) as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), e.code
        
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': "An error occurred during login"
            }), 500

    @api.route('/scrape', methods=['POST'])
    @token_required
    def scrape_url():
        """Scrape content from a URL."""
        try:
            data = request.get_json()
            if not data:
                raise BadRequest("No input data provided")
            
            url = data.get('url')
            if not url:
                raise BadRequest("URL is required")
            
            result = ScraperService().scrape_and_save(url)
            return jsonify({
                'status': 'success',
                'data': result
            }), 200
        
        except BadRequest as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 400
        
        except Exception as e:
            logger.error(f"Error scraping URL: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @api.route('/campaigns', methods=['POST'])
    @token_required
    @log_function_call
    def create_campaign():
        """
        Create a campaign and fetch leads from Apollo API, saving them to the database.
        """
        try:
            params = request.get_json()
            required_params = ['count', 'excludeGuessedEmails', 'excludeNoEmails', 'getEmails', 'searchUrl']
            for param in required_params:
                if param not in params:
                    raise BadRequest(f"Missing required parameter: {param}")

            result = campaign_service.create_campaign_with_leads(params)

            return jsonify(result), 201
        except BadRequest as e:
            return jsonify({'status': 'error', 'message': str(e)}), 400
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @api.route('/leads', methods=['GET'])
    @token_required
    def get_leads():
        """Get all leads for the current user."""
        try:
            lead_service = LeadService()
            leads = lead_service.get_leads(g.current_user.id)
            return jsonify({
                'status': 'success',
                'data': leads
            }), 200
        
        except Exception as e:
            logger.error(f"Error fetching leads: {str(e)}")
            raise

    @api.route('/leads', methods=['POST'])
    @token_required
    def create_lead():
        """Create a new lead."""
        try:
            data = request.get_json()
            if not data:
                raise BadRequest("No input data provided")
            
            lead_service = LeadService()
            lead = lead_service.create_lead(user_id=g.current_user.id, data=data)
            return jsonify({
                'status': 'success',
                'data': lead
            }), 201
        
        except BadRequest as e:
            raise
        
        except Exception as e:
            logger.error(f"Error creating lead: {str(e)}")
            raise

    @api.route('/leads/<lead_id>', methods=['GET'])
    @token_required
    def get_lead(lead_id):
        """Get a specific lead."""
        try:
            lead_service = LeadService()
            lead = lead_service.get_lead(user_id=g.current_user.id, lead_id=lead_id)
            if not lead:
                raise NotFound("Lead not found")
            
            return jsonify({
                'status': 'success',
                'data': lead
            }), 200
        
        except NotFound as e:
            raise
        
        except Exception as e:
            logger.error(f"Error fetching lead: {str(e)}")
            raise

    @api.route('/leads/<lead_id>', methods=['PUT'])
    @token_required
    def update_lead(lead_id):
        """Update a specific lead."""
        try:
            data = request.get_json()
            if not data:
                raise BadRequest("No input data provided")
            
            lead_service = LeadService()
            lead = lead_service.update_lead(user_id=g.current_user.id, lead_id=lead_id, data=data)
            if not lead:
                raise NotFound("Lead not found")
            
            return jsonify({
                'status': 'success',
                'data': lead
            }), 200
        
        except (NotFound, BadRequest) as e:
            raise
        
        except Exception as e:
            logger.error(f"Error updating lead: {str(e)}")
            raise

    @api.route('/leads/<lead_id>', methods=['DELETE'])
    @token_required
    def delete_lead(lead_id):
        """Delete a specific lead."""
        try:
            lead_service = LeadService()
            success = lead_service.delete_lead(user_id=g.current_user.id, lead_id=lead_id)
            if not success:
                raise NotFound("Lead not found")
            
            return jsonify({
                'status': 'success',
                'message': 'Lead deleted successfully'
            }), 200
        
        except NotFound as e:
            raise
        
        except Exception as e:
            logger.error(f"Error deleting lead: {str(e)}")
            raise

    @api.route('/organizations', methods=['POST'])
    @token_required
    def create_organization():
        logger.debug('POST /organizations called')
        data = request.get_json()
        logger.debug(f'Request data: {data}')
        if not data or 'name' not in data:
            logger.debug('Missing name in request data')
            raise BadRequest('Name is required')
        org = organization_service.create_organization(data)
        logger.debug(f'Organization created: {org}')
        return jsonify({'status': 'success', 'data': org}), 201

    @api.route('/organizations', methods=['GET'])
    @token_required
    def get_organizations():
        logger.debug('GET /organizations called')
        orgs = organization_service.get_organizations()
        logger.debug(f'Returning organizations: {orgs}')
        return jsonify({'status': 'success', 'data': orgs}), 200

    @api.route('/organizations/<org_id>', methods=['GET'])
    @token_required
    def get_organization(org_id):
        org = organization_service.get_organization(org_id)
        if not org:
            raise NotFound('Organization not found')
        return jsonify({'status': 'success', 'data': org}), 200

    @api.route('/organizations/<org_id>', methods=['PUT'])
    @token_required
    def update_organization(org_id):
        data = request.get_json()
        if not data:
            raise BadRequest('No input data provided')
        org = organization_service.update_organization(org_id, data)
        if not org:
            raise NotFound('Organization not found')
        return jsonify({'status': 'success', 'data': org}), 200

    @api.route('/events', methods=['POST'])
    @token_required
    def create_event():
        data = request.get_json()
        if not data or not all(k in data for k in ('source', 'tag', 'data', 'type')):
            raise BadRequest('Missing required event fields')
        event = event_service.create_event(data)
        return jsonify({'status': 'success', 'data': event}), 201

    @api.route('/events', methods=['GET'])
    @token_required
    def get_events():
        events = event_service.get_events()
        return jsonify({'status': 'success', 'data': events}), 200

    @api.route('/events/<event_id>', methods=['GET'])
    @token_required
    def get_event(event_id):
        event = event_service.get_event(event_id)
        return jsonify({'status': 'success', 'data': event}), 200 