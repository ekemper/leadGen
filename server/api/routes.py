from flask import jsonify, request, g, current_app, abort
from email_validator import validate_email, EmailNotValidError
from datetime import datetime, timedelta
import bcrypt
import jwt
import os
import re
import uuid
from server.models import User, Campaign, Job
from server.config.database import db
from server.utils.logging_config import app_logger
from werkzeug.exceptions import BadRequest, Unauthorized, NotFound, InternalServerError
from server.api.services.auth_service import AuthService
from server.api.services.scraper_service import ScraperService
from server.api.services.lead_service import LeadService
import json
from flask import Blueprint
from server.background_services.apollo_service import ApolloService
from server.utils.middleware import log_function_call
from functools import wraps
from server.api.services.organization_service import OrganizationService
from server.api.services.event_service import EventService
from server.api.schemas import (
    CampaignSchema, CampaignCreateSchema, CampaignStartSchema,
    ErrorResponseSchema, SuccessResponseSchema, JobSchema
)
import threading
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from server.extensions import limiter

# Create blueprint
api = Blueprint('api', __name__)

# Service factory functions
def get_scraper_service():
    return ScraperService()

def get_apollo_service():
    return ApolloService()

def get_lead_service():
    return LeadService()

def get_campaign_service():
    from server.api.services.campaign_service import CampaignService
    return CampaignService()

def get_organization_service():
    return OrganizationService()

def get_event_service():
    return EventService()

# Add after other service initializations
_cleanup_locks = {}

def _get_cleanup_lock(campaign_id):
    """Get or create a lock for campaign cleanup."""
    if campaign_id not in _cleanup_locks:
        _cleanup_locks[campaign_id] = threading.Lock()
    return _cleanup_locks[campaign_id]

def token_required(f):
    """Decorator to protect routes with JWT authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == 'OPTIONS':
            return '', 200
        token = None
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        app_logger.debug(f"Auth header: {auth_header}")
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            app_logger.debug(f"Token extracted: {token[:10]}...")
        
        if not token:
            app_logger.error("No token found in request")
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 401,
                    'name': 'Unauthorized',
                    'message': 'Token is missing'
                }
            }), 401
            
        try:
            # Decode the token
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.filter_by(id=data['user_id']).first()
            
            if not current_user:
                app_logger.error(f"User not found for token: {token[:10]}...")
                return jsonify({
                    'status': 'error',
                    'error': {
                        'code': 401,
                        'name': 'Unauthorized',
                        'message': 'User not found'
                    }
                }), 401
                
            # Add user to request context
            g.current_user = current_user
            return f(*args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            app_logger.error("Token has expired")
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 401,
                    'name': 'Unauthorized',
                    'message': 'Token has expired'
                }
            }), 401
            
        except jwt.InvalidTokenError as e:
            app_logger.error(f"Invalid token: {str(e)}")
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 401,
                    'name': 'Unauthorized',
                    'message': 'Invalid token'
                }
            }), 401
            
    return decorated

def register_routes(api):
    """Register all routes with the provided blueprint."""
    
    @api.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint (public, no auth)."""
        app_logger.debug('Health check endpoint called')
        return jsonify({
            'status': 'healthy',
            'message': 'API is running',
            'endpoint': '/api/health'
        }), 200

    @api.route('/')
    def root():
        """Root endpoint (public, no auth)."""
        return jsonify({
            'message': 'Welcome to the Auth Template API',
            'version': '1.0.0'
        }), 200

    # Public routes (no token required)
    @api.route('/auth/signup', methods=['POST'])
    def signup():
        """Handle user registration."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'status': 'error',
                    'error': {
                        'code': 400,
                        'name': 'Bad Request',
                        'message': 'No input data provided'
                    }
                }), 400
            
            email = data.get('email')
            password = data.get('password')
            confirm_password = data.get('confirm_password')
            
            if not all([email, password, confirm_password]):
                return jsonify({
                    'status': 'error',
                    'error': {
                        'code': 400,
                        'name': 'Bad Request',
                        'message': 'All fields are required'
                    }
                }), 400
            
            result = AuthService.signup(email, password, confirm_password)
            return jsonify({
                'status': 'success',
                'data': result
            }), 201
        
        except BadRequest as e:
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 400,
                    'name': 'Bad Request',
                    'message': str(e)
                }
            }), 400
        
        except Exception as e:
            app_logger.error(f"Error during signup: {str(e)}")
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 400,
                    'name': 'Bad Request',
                    'message': str(e)
                }
            }), 400

    @api.route('/auth/login', methods=['POST'])
    def login():
        """Handle user login."""
        try:
            data = request.get_json()
            # Log only non-sensitive info
            app_logger.info(f"LOGIN ATTEMPT: Email: {data.get('email', '[MISSING]')}, Headers: {dict(request.headers)}, Content-Type: {request.content_type}")
            if not data:
                return jsonify({
                    'status': 'error',
                    'error': {
                        'code': 400,
                        'name': 'Bad Request',
                        'message': 'No input data provided'
                    }
                }), 400

            auth_service = AuthService()
            result = auth_service.login(data)
            return jsonify({
                'status': 'success',
                'data': result
            }), 200
        except Unauthorized as e:
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 401,
                    'name': 'Unauthorized',
                    'message': str(e)
                }
            }), 401
        except Exception as e:
            app_logger.error(f"LOGIN ERROR: {str(e)}", exc_info=True)
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 500,
                    'name': 'Internal Server Error',
                    'message': str(e)
                }
            }), 500

    # Protected routes (token required)
    @api.route('/scrape', methods=['POST'])
    @token_required
    def scrape_url():
        """Scrape a URL for contact information."""
        try:
            data = request.get_json()
            if not data or 'url' not in data:
                raise BadRequest("URL is required")
            
            scraper_service = get_scraper_service()
            result = scraper_service.scrape_url(data['url'])
            return jsonify(result), 200
            
        except Exception as e:
            app_logger.error(f"Error during scraping: {str(e)}")
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 400,
                    'name': 'Bad Request',
                    'message': str(e)
                }
            }), 400

    @api.route('/campaigns', methods=['GET'])
    @token_required
    def get_campaigns():
        """Get all campaigns for the current user."""
        try:
            campaign_service = get_campaign_service()
            campaigns = campaign_service.get_campaigns()
            return jsonify({'status': 'success', 'data': {'campaigns': campaigns}}), 200
        except Exception as e:
            app_logger.error(f"Error getting campaigns: {str(e)}")
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 500,
                    'name': 'Internal Server Error',
                    'message': str(e)
                }
            }), 500

    @api.route('/campaigns/<campaign_id>', methods=['GET'])
    @token_required
    def get_campaign(campaign_id):
        """Get a single campaign by ID."""
        try:
            campaign_service = get_campaign_service()
            campaign = campaign_service.get_campaign(campaign_id)
            if not campaign:
                error_response = {
                    'status': 'error',
                    'error': {
                        'code': 404,
                        'name': 'Not Found',
                        'message': 'Campaign not found'
                    }
                }
                errors = ErrorResponseSchema().validate(error_response)
                if errors:
                    app_logger.error(f"Invalid error response format: {errors}")
                return jsonify(error_response), 404
                
            # Validate campaign data
            errors = CampaignSchema().validate(campaign)
            if errors:
                raise ValueError(f"Invalid campaign data: {errors}")
                
            response_data = {
                'status': 'success',
                'data': campaign
            }
            
            # Validate response format
            errors = SuccessResponseSchema().validate(response_data)
            if errors:
                raise ValueError(f"Invalid response format: {errors}")
                
            return jsonify(response_data), 200
            
        except Exception as e:
            app_logger.error(f"Error fetching campaign: {str(e)}")
            error_response = {
                'status': 'error',
                'error': {
                    'code': 500,
                    'name': 'Internal Server Error',
                    'message': 'Failed to fetch campaign'
                }
            }
            errors = ErrorResponseSchema().validate(error_response)
            if errors:
                app_logger.error(f"Invalid error response format: {errors}")
            return jsonify(error_response), 500

    @api.route('/campaigns/<campaign_id>/details', methods=['GET'])
    @token_required
    def get_campaign_details(campaign_id):
        """Get campaign details including lead stats and Instantly analytics."""
        try:
            campaign_service = get_campaign_service()
            campaign = campaign_service.get_campaign(campaign_id)
            if not campaign:
                return jsonify({
                    'status': 'error',
                    'error': {
                        'code': 404,
                        'name': 'Not Found',
                        'message': 'Campaign not found'
                    }
                }), 404

            lead_stats = campaign_service.get_campaign_lead_stats(campaign_id)
            instantly_analytics = campaign_service.get_campaign_instantly_analytics(campaign)
            response_data = {
                'status': 'success',
                'data': {
                    'campaign': campaign,
                    'lead_stats': lead_stats,
                    'instantly_analytics': instantly_analytics
                }
            }
            return jsonify(response_data), 200
        except Exception as e:
            app_logger.error(f"Error fetching campaign details: {str(e)}")
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 500,
                    'name': 'Internal Server Error',
                    'message': 'Failed to fetch campaign details'
                }
            }), 500

    @api.route('/campaigns/<campaign_id>', methods=['PATCH'])
    @token_required
    def update_campaign(campaign_id):
        """Update campaign properties."""
        data = request.get_json()
        if not data:
            return make_error_response(400, 'Bad Request', 'No data provided')
        allowed_fields = {'name', 'description', 'fileName', 'totalRecords', 'url'}
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        if not update_data:
            return make_error_response(400, 'Bad Request', 'No valid fields to update')
        try:
            campaign_service = get_campaign_service()
            updated = campaign_service.update_campaign(campaign_id, update_data)
            errors = CampaignSchema().validate(updated)
            if errors:
                return make_error_response(400, 'Bad Request', f'Invalid campaign data: {errors}')
            return jsonify({'status': 'success', 'data': updated}), 200
        except Exception as e:
            app_logger.error(f"Error updating campaign: {str(e)}")
            return make_error_response(500, 'Internal Server Error', 'Failed to update campaign')

    # --- Error response helper ---
    def make_error_response(code, name, message, status_code=400):
        error_response = {
            'status': 'error',
            'error': {
                'code': code,
                'name': name,
                'message': message
            }
        }
        errors = ErrorResponseSchema().validate(error_response)
        if errors:
            app_logger.error(f"Invalid error response format: {errors}")
        return jsonify(error_response), status_code

    @api.route('/campaigns', methods=['POST'])
    @token_required
    def create_campaign():
        """
        Create a new campaign.

        Request JSON fields:
          - name (str, required)
          - description (str, required)
          - organization_id (str, required)
          - fileName (str, required)
          - totalRecords (int, required)
          - url (str, required)
        """
        data = request.get_json()
        app_logger.info(f"Received campaign creation request: {json.dumps(data, default=str)}")

        if not data:
            return make_error_response(400, 'Bad Request', 'No data provided')

        errors = CampaignCreateSchema().validate(data)
        if errors:
            app_logger.warning(f"Validation errors during campaign creation: {errors}")
            return make_error_response(400, 'Bad Request', str(errors))

        try:
            campaign_service = get_campaign_service()
            result = campaign_service.create_campaign(data)

            # Validate response data
            errors = CampaignSchema().validate(result)
            if errors:
                app_logger.error(f"Response validation errors after campaign creation: {errors}")
                return make_error_response(500, 'Internal Server Error', f"Invalid campaign data: {errors}", status_code=500)

            response_data = {'status': 'success', 'data': result}
            errors = SuccessResponseSchema().validate(response_data)
            if errors:
                app_logger.error(f"Response format validation errors: {errors}")
                return make_error_response(500, 'Internal Server Error', f"Invalid response format: {errors}", status_code=500)

            return jsonify(response_data), 201

        except ValueError as e:
            app_logger.warning(f"ValueError during campaign creation: {str(e)}")
            return make_error_response(400, 'Bad Request', str(e))
        except Exception as e:
            app_logger.error(f"Error creating campaign: {str(e)}", exc_info=True)
            app_logger.error(f"Request data that caused error: {json.dumps(data, default=str)}")
            return make_error_response(500, 'Internal Server Error', 'Failed to create campaign', status_code=500)

    @api.route('/campaigns/<campaign_id>/start', methods=['POST', 'OPTIONS'])
    @token_required
    @log_function_call
    def start_campaign(campaign_id):
        """Start the lead generation process for an existing campaign."""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            # Start campaign
            campaign_service = get_campaign_service()
            campaign_data = campaign_service.start_campaign(campaign_id)
            
            # Validate response data
            errors = CampaignSchema().validate(campaign_data)
            if errors:
                raise ValueError(f"Invalid campaign data: {errors}")
                
            response_data = {
                'status': 'success',
                'data': campaign_data
            }
            
            # Validate response format
            errors = SuccessResponseSchema().validate(response_data)
            if errors:
                raise ValueError(f"Invalid response format: {errors}")
                
            return jsonify(response_data), 200

        except ValueError as e:
            error_response = {
                'status': 'error',
                'error': {
                    'code': 400,
                    'name': 'Bad Request',
                    'message': str(e)
                }
            }
            errors = ErrorResponseSchema().validate(error_response)
            if errors:
                app_logger.error(f"Invalid error response format: {errors}")
            return jsonify(error_response), 400
            
        except Exception as e:
            app_logger.error(f"Error starting campaign: {str(e)}")
            error_response = {
                'status': 'error',
                'error': {
                    'code': 500,
                    'name': 'Internal Server Error',
                    'message': 'Internal server error'
                }
            }
            errors = ErrorResponseSchema().validate(error_response)
            if errors:
                app_logger.error(f"Invalid error response format: {errors}")
            return jsonify(error_response), 500

    @api.route('/leads', methods=['GET'])
    @token_required
    def get_leads():
        """Get all leads for the current user, optionally filtered by campaign_id."""
        try:
            lead_service = get_lead_service()
            campaign_id = request.args.get('campaign_id')
            if campaign_id:
                # Validate campaign_id is a real campaign
                from server.models import Campaign
                campaign = Campaign.query.get(campaign_id)
                if not campaign:
                    return jsonify({
                        'status': 'error',
                        'error': {
                            'code': 400,
                            'name': 'Bad Request',
                            'message': f'Invalid campaign_id: {campaign_id}'
                        }
                    }), 400
            leads = lead_service.get_leads(campaign_id=campaign_id)
            return jsonify({
                'status': 'success',
                'data': {
                    'leads': leads
                }
            }), 200
        except Exception as e:
            app_logger.error(f"Error getting leads: {str(e)}")
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 500,
                    'name': 'Internal Server Error',
                    'message': str(e)
                }
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
                    'error': {
                        'code': 400,
                        'name': 'Bad Request',
                        'message': 'No input data provided'
                    }
                }), 400
            
            lead_service = get_lead_service()
            lead = lead_service.create_lead(data=data)
            return jsonify({
                'status': 'success',
                'data': lead
            }), 201
        
        except BadRequest as e:
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 400,
                    'name': 'Bad Request',
                    'message': str(e)
                }
            }), 400
        
        except Exception as e:
            app_logger.error(f"Error creating lead: {str(e)}")
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 500,
                    'name': 'Internal Server Error',
                    'message': str(e)
                }
            }), 500

    @api.route('/leads/<lead_id>', methods=['GET'])
    @token_required
    def get_lead(lead_id):
        """Get a specific lead by ID."""
        try:
            lead_service = get_lead_service()
            lead = lead_service.get_lead(lead_id=lead_id)
            if not lead:
                return jsonify({
                    'status': 'error',
                    'error': {
                        'code': 404,
                        'name': 'Not Found',
                        'message': f'Lead {lead_id} not found'
                    }
                }), 404
            return jsonify({
                'status': 'success',
                'data': lead
            }), 200
        except NotFound as e:
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 404,
                    'name': 'Not Found',
                    'message': str(e)
                }
            }), 404
        except Exception as e:
            app_logger.error(f"Error fetching lead: {str(e)}")
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 500,
                    'name': 'Internal Server Error',
                    'message': str(e)
                }
            }), 500

    @api.route('/leads/<lead_id>', methods=['PUT'])
    @token_required
    def update_lead(lead_id):
        """Update a specific lead."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'status': 'error',
                    'error': {
                        'code': 400,
                        'name': 'Bad Request',
                        'message': 'No input data provided'
                    }
                }), 400
            
            lead_service = get_lead_service()
            lead = lead_service.update_lead(lead_id=lead_id, data=data)
            return jsonify({
                'status': 'success',
                'data': lead
            }), 200
        
        except NotFound as e:
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 404,
                    'name': 'Not Found',
                    'message': str(e)
                }
            }), 404
        
        except BadRequest as e:
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 400,
                    'name': 'Bad Request',
                    'message': str(e)
                }
            }), 400
        
        except Exception as e:
            app_logger.error(f"Error updating lead: {str(e)}")
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 500,
                    'name': 'Internal Server Error',
                    'message': str(e)
                }
            }), 500

    @api.route('/organizations', methods=['GET'])
    @token_required
    def get_organizations():
        """Get all organizations for the current user."""
        try:
            organization_service = get_organization_service()
            organizations = organization_service.get_organizations()
            return jsonify({'status': 'success', 'data': {'organizations': organizations}}), 200
        except Exception as e:
            app_logger.error(f"Error getting organizations: {str(e)}")
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 500,
                    'name': 'Internal Server Error',
                    'message': str(e)
                }
            }), 500

    @api.route('/organizations', methods=['POST'])
    @token_required
    def create_organization():
        try:
            data = request.get_json()
            if not data:
                return jsonify({'status': 'error', 'error': {'code': 400, 'name': 'Bad Request', 'message': 'No data provided'}}), 400

            organization_service = get_organization_service()
            result = organization_service.create_organization(data)
            return jsonify({'status': 'success', 'data': result}), 201
        except ValueError as e:
            return jsonify({'status': 'error', 'error': {'code': 400, 'name': 'Bad Request', 'message': str(e)}}), 400
        except Exception as e:
            app_logger.error(f"Error creating organization: {str(e)}")
            return jsonify({'status': 'error', 'error': {'code': 500, 'name': 'Internal Server Error', 'message': 'Internal server error'}}), 500

    @api.route('/organizations/<org_id>', methods=['GET'])
    @token_required
    def get_organization(org_id):
        org = get_organization_service().get_organization(org_id)
        if not org:
            return jsonify({'status': 'error', 'error': {'code': 404, 'name': 'Not Found', 'message': 'Organization not found'}}), 404
        return jsonify({'status': 'success', 'data': org}), 200

    @api.route('/organizations/<org_id>', methods=['PUT'])
    @token_required
    def update_organization(org_id):
        try:
            data = request.get_json()
            if not data:
                return jsonify({'status': 'error', 'error': {'code': 400, 'name': 'Bad Request', 'message': 'No data provided'}}), 400

            organization_service = get_organization_service()
            result = organization_service.update_organization(org_id, data)
            if result is None:
                return jsonify({'status': 'error', 'error': {'code': 404, 'name': 'Not Found', 'message': 'Organization not found'}}), 404
            return jsonify({'status': 'success', 'data': result}), 200
        except ValueError as e:
            return jsonify({'status': 'error', 'error': {'code': 400, 'name': 'Bad Request', 'message': str(e)}}), 400
        except Exception as e:
            app_logger.error(f"Error updating organization: {str(e)}")
            return jsonify({'status': 'error', 'error': {'code': 500, 'name': 'Internal Server Error', 'message': 'Internal server error'}}), 500

    @api.route('/events', methods=['POST'])
    @limiter.limit("1000 per hour")
    @token_required
    def create_event():
        """Create a new event."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'status': 'error',
                    'error': {
                        'code': 400,
                        'name': 'Bad Request',
                        'message': 'No data provided'
                    }
                }), 400

            # Special handling for console logs
            if data.get('tag') == 'console' and data.get('source') == 'browser':
                event_service = get_event_service()
                result = event_service.handle_console_logs(data['data'])
            else:
                event_service = get_event_service()
                result = event_service.create_event(data)

            return jsonify({
                'status': 'success',
                'data': result
            }), 201
        except Exception as e:
            app_logger.error(f"Error creating event: {str(e)}")
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 500,
                    'name': 'Internal Server Error',
                    'message': 'Failed to create event'
                }
            }), 500

    @api.route('/events', methods=['GET'])
    @token_required
    def get_events():
        """Get all events for the current user."""
        try:
            event_service = get_event_service()
            events = event_service.get_events()
            return jsonify({'status': 'success', 'data': {'events': events}}), 200
        except Exception as e:
            app_logger.error(f"Error getting events: {str(e)}")
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 500,
                    'name': 'Internal Server Error',
                    'message': str(e)
                }
            }), 500

    @api.route('/events/<event_id>', methods=['GET'])
    @token_required
    def get_event(event_id):
        event = get_event_service().get_event(event_id)
        return jsonify({'status': 'success', 'data': event}), 200

    @api.route('/auth/me', methods=['GET'])
    @token_required
    def get_current_user():
        """Get current user information."""
        try:
            current_user = g.current_user
            return jsonify({
                'status': 'success',
                'data': {
                    'id': current_user.id,
                    'email': current_user.email,
                    'created_at': current_user.created_at.isoformat(),
                    'updated_at': current_user.updated_at.isoformat()
                }
            }), 200
        except Exception as e:
            app_logger.error(f"Error getting current user: {str(e)}")
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 500,
                    'name': 'Internal Server Error',
                    'message': str(e)
                }
            }), 500

    @api.route('/campaigns/<campaign_id>/results', methods=['GET'])
    @token_required
    def get_campaign_results(campaign_id):
        """Get campaign results."""
        try:
            # Get campaign
            campaign_service = get_campaign_service()
            campaign = campaign_service.get_campaign(campaign_id)
            if not campaign:
                return jsonify({
                    'status': 'error',
                    'error': {
                        'code': 404,
                        'name': 'Not Found',
                        'message': f'Campaign {campaign_id} not found'
                    }
                }), 404

            # Get completed jobs
            completed_jobs = Job.query.filter_by(
                campaign_id=campaign_id,
                status='COMPLETED'
            ).all()

            if not completed_jobs:
                return jsonify({
                    'status': 'error',
                    'error': {
                        'code': 404,
                        'name': 'Not Found',
                        'message': 'No completed jobs found for this campaign'
                    }
                }), 404

            # Validate job results
            results = {}
            for job in completed_jobs:
                try:
                    Job.validate_result(job.job_type, job.result)
                    results[job.job_type] = job.result
                except ValueError as e:
                    return jsonify({
                        'status': 'error',
                        'error': {
                            'code': 404,
                            'name': 'Not Found',
                            'message': str(e)
                        }
                    }), 404

            return jsonify({
                'status': 'success',
                'data': {
                    'campaign': campaign.to_dict(),
                    'results': results
                }
            }), 200

        except Exception as e:
            app_logger.error(f"Error getting campaign results: {str(e)}")
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 500,
                    'name': 'Internal Server Error',
                    'message': 'Internal server error'
                }
            }), 500

    @api.route('/campaigns/<campaign_id>/cleanup', methods=['POST'])
    @token_required
    def cleanup_campaign_jobs(campaign_id):
        """Clean up old jobs for a campaign."""
        try:
            data = request.get_json()
            if not data or 'days' not in data:
                return jsonify({
                    'status': 'error',
                    'error': {
                        'code': 400,
                        'name': 'Bad Request',
                        'message': 'Days parameter is required'
                    }
                }), 400

            days = int(data['days'])
            if days <= 0:
                return jsonify({
                    'status': 'error',
                    'error': {
                        'code': 400,
                        'name': 'Bad Request',
                        'message': 'Days must be a positive integer'
                    }
                }), 400

            campaign_service = get_campaign_service()
            campaign = campaign_service.get_campaign(campaign_id)
            if not campaign:
                return jsonify({
                    'status': 'error',
                    'error': {
                        'code': 404,
                        'name': 'Not Found',
                        'message': 'Campaign not found'
                    }
                }), 404

            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Use a transaction for the cleanup operation
            with db.session.begin_nested():
                # Delete jobs older than cutoff date, excluding test jobs
                deleted = Job.query.filter(
                    Job.campaign_id == campaign_id,
                    Job.created_at < cutoff_date,
                    ~Job.id.like('test-%')  # Exclude test jobs
                ).delete()
            
            db.session.commit()

            return jsonify({
                'status': 'success',
                'message': f'Successfully cleaned up {deleted} old jobs'
            })

        except Exception as e:
            db.session.rollback()
            app_logger.error(f"Error cleaning up campaign jobs: {str(e)}")
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 500,
                    'name': 'Internal Server Error',
                    'message': 'Failed to clean up campaign jobs'
                }
            }), 500

    @api.route('/jobs', methods=['GET'])
    @token_required
    @limiter.limit("2000 per hour")
    def get_jobs():
        """Get jobs, optionally filtered by campaign_id."""
        from server.api.services.job_service import JobService
        job_service = JobService()
        campaign_id = request.args.get('campaign_id')
        jobs = job_service.get_jobs(campaign_id=campaign_id)
        # Validate each job
        for job in jobs:
            errors = JobSchema().validate(job)
            if errors:
                return jsonify({
                    'status': 'error',
                    'error': {
                        'code': 500,
                        'name': 'Internal Server Error',
                        'message': f'Invalid job data: {errors}'
                    }
                }), 500
        return jsonify({
            'status': 'success',
            'data': {'jobs': jobs}
        }), 200 