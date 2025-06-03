import os
from apify_client import ApifyClient
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import random
import time
from datetime import datetime
import json
import traceback
import apify_client
from sqlalchemy.orm import Session
from app.models.lead import Lead
from app.models.campaign import Campaign
from app.models.job import Job, JobStatus
from app.schemas.lead import LeadCreate
from app.core.database import get_db
from app.core.logger import get_logger
from app.core.api_integration_rate_limiter import ApiIntegrationRateLimiter
from app.background_services.smoke_tests.mock_apify_client import MockApifyClient
from app.core.config import settings

logger = get_logger(__name__)

"""
IMPORTANT: Apify Python client (v1.10.0 and some other versions) expects webhook payload keys in snake_case (e.g., 'event_types', 'request_url', 'payload_template', 'idempotency_key'),
even though the official Apify API docs use camelCase (e.g., 'eventTypes', 'requestUrl', 'payloadTemplate', 'idempotencyKey').

If you use camelCase keys, you will get KeyError exceptions from the client library (e.g., 'event_types', 'request_url').

References:
- https://docs.apify.com/platform/integrations/webhooks/events (API docs, camelCase)
- https://github.com/apify/apify-client-python/blob/master/src/apify_client/_utils.py (client expects snake_case)
- Error example: KeyError: 'event_types' or 'request_url' in encode_webhook_list_to_base64

This is an exception to the usual rule of following the API docs exactly. Always use snake_case keys in webhook payloads when using the Apify Python client.
"""

class ApolloService:
    """
    Service for interacting with the Apollo API via Apify.
    
    This service now supports rate limiting to prevent exceeding API limits
    and avoid IP blocking. Rate limiting is optional to maintain backward 
    compatibility with existing code.
    
    Note: Apollo service typically handles bulk operations, so rate limiting
    is applied per API call rather than per lead processed.
    """
    
    def __init__(self, rate_limiter: Optional[ApiIntegrationRateLimiter] = None):
        self.settings = settings
        
        # Set actor ID and API token properties
        self.actor_id = settings.APOLLO_ACTOR_ID
        self.api_token = settings.APIFY_API_TOKEN
        
        # Initialize rate limiter - prefer passed parameter, fallback to internal setup
        if rate_limiter:
            self.rate_limiter = rate_limiter
            logger.info("Apollo service - Using provided rate limiter")
        else:
            # Initialize rate limiter with Redis connection
            try:
                from app.core.config import get_redis_connection
                redis_client = get_redis_connection()
                self.rate_limiter = ApiIntegrationRateLimiter(
                    redis_client=redis_client,
                    api_name="Apollo",
                    max_requests=settings.APOLLO_RATE_LIMIT_REQUESTS,
                    period_seconds=settings.APOLLO_RATE_LIMIT_PERIOD
                )
                logger.info("Apollo service - Using internal rate limiter setup")
            except Exception as e:
                logger.warning(f"Failed to initialize rate limiter: {e}. Proceeding without rate limiting.")
                self.rate_limiter = None
        
        # Determine which Apify client to use
        use_mock = os.getenv('USE_APIFY_CLIENT_MOCK', 'false').lower() == 'true'
        logger.info(f"Apollo service - USE_APIFY_CLIENT_MOCK env var: {os.getenv('USE_APIFY_CLIENT_MOCK', 'not set')}")
        logger.info(f"Apollo service - Using mock client: {use_mock}")
        
        if use_mock:
            try:
                from app.background_services.smoke_tests.mock_apify_client import MockApifyClient
                self.apify_client = MockApifyClient()
                logger.info("Apollo service - Successfully initialized with MockApifyClient")
            except ImportError as e:
                logger.error(f"Apollo service - Failed to import MockApifyClient: {e}")
                logger.info("Apollo service - Falling back to real ApifyClient")
                self.apify_client = ApifyClient(token=settings.APIFY_API_TOKEN)
        else:
            self.apify_client = ApifyClient(token=settings.APIFY_API_TOKEN)
            logger.info("Apollo service - Initialized with real ApifyClient")
        
        logger.info(f"ApolloService initialized with rate limiting: {settings.APOLLO_RATE_LIMIT_REQUESTS} requests per {settings.APOLLO_RATE_LIMIT_PERIOD}s", extra={"rate_limiting": "enabled"})

    def _save_leads_to_db(self, leads_data: List[Dict[str, Any]], campaign_id: str, db) -> Dict[str, int]:
        """
        Helper to save leads to the database session and commit.
        Prevents duplicate emails from being created.
        Returns detailed statistics about the operation.
        """
        if not db:
            logger.warning("No database session provided, skipping lead save")
            return {'created': 0, 'skipped': 0, 'errors': 0}
        
        if not leads_data:
            logger.info("No leads data provided, returning 0")
            return {'created': 0, 'skipped': 0, 'errors': 0}
            
        # Extract all emails from the incoming leads data (filter out None/empty emails)
        # Note: We still process ALL records, but only check duplicates for valid emails
        incoming_emails = [
            lead_data.get('email', '').strip().lower() 
            for lead_data in leads_data 
            if lead_data.get('email') and lead_data.get('email').strip()
        ]
        
        # Batch check for existing emails in the database (only for valid emails)
        existing_emails = set()
        if incoming_emails:  # Only check if we have valid emails to check
            try:
                existing_emails_query = db.query(Lead.email).filter(
                    Lead.email.isnot(None),
                    Lead.email.in_(incoming_emails)
                ).all()
                existing_emails = {email[0].lower() for email in existing_emails_query}
                
                logger.info(f"[LEAD] Found {len(existing_emails)} existing emails out of {len(incoming_emails)} incoming emails")
                
            except Exception as e:
                logger.error(f"[LEAD] Error checking existing emails: {str(e)}")
                # Continue without duplicate checking if query fails
                existing_emails = set()
            
        created_count = 0
        skipped_count = 0
        error_count = 0
        
        # Process ALL records individually (including those with invalid emails)
        for lead_data in leads_data:
            try:
                email = lead_data.get('email')
                if not email or not email.strip():
                    logger.warning(f"[LEAD] Skipping lead with empty email: {lead_data.get('first_name', 'unknown')} {lead_data.get('last_name', '')}")
                    skipped_count += 1
                    continue
                
                email_normalized = email.strip().lower()
                
                # Check if this email already exists (only for valid emails)
                if email_normalized in existing_emails:
                    logger.info(f"[LEAD] Skipping duplicate email: {email} for campaign {campaign_id}")
                    skipped_count += 1
                    continue
                
                # Extract company name from organization or use organization_name field
                company = None
                if 'organization' in lead_data and lead_data['organization']:
                    company = lead_data['organization'].get('name')
                elif 'organization_name' in lead_data:
                    company = lead_data['organization_name']
                
                # Create Lead object
                lead = Lead(
                    campaign_id=campaign_id,
                    first_name=lead_data.get('first_name'),
                    last_name=lead_data.get('last_name'),
                    email=email.strip(),  # Store original case but trimmed
                    phone=lead_data.get('phone'),
                    company=company,
                    title=lead_data.get('title'),
                    linkedin_url=lead_data.get('linkedin_url'),
                    raw_data=lead_data  # Store the full raw data
                )
                
                db.add(lead)
                
                # Add this email to our existing set to prevent duplicates within this batch
                existing_emails.add(email_normalized)
                
                created_count += 1
                logger.info(f"[LEAD] Created lead: {lead.email} for campaign {campaign_id}")
                
            except Exception as e:
                logger.error(f"[LEAD] Error creating lead from data {lead_data.get('email', 'unknown')}: {str(e)}")
                error_count += 1
                continue
        
        # Commit all leads at once
        try:
            db.commit()
            logger.info(f"[LEAD] Successfully saved {created_count} leads for campaign {campaign_id}")
            if skipped_count > 0:
                logger.info(f"[LEAD] Skipped {skipped_count} duplicate/invalid emails for campaign {campaign_id}")
            if error_count > 0:
                logger.warning(f"[LEAD] Encountered {error_count} errors while processing leads for campaign {campaign_id}")
        except Exception as e:
            logger.error(f"[LEAD] Error committing leads to database: {str(e)}")
            db.rollback()
            raise
            
        return {
            'created': created_count,
            'skipped': skipped_count,
            'errors': error_count
        }

    def fetch_leads(self, params: Dict[str, Any], campaign_id: str, db=None) -> Dict[str, Any]:
        """
        Fetch leads from Apollo via Apify and save them to the database.
        
        This method now includes rate limiting support to prevent exceeding
        API limits. If rate limiting is enabled and the limit is exceeded,
        the method will return an error response.
        
        Args:
            params: Parameters for the Apollo API (must include fileName, totalRecords, url)
            campaign_id: ID of the campaign to associate leads with
            db: Database session (optional, for FastAPI integration)
            
        Returns:
            Dict containing the count of created leads and any errors
        """
        # Validate input shape
        required_keys = ['fileName', 'totalRecords', 'url']
        for key in required_keys:
            if key not in params:
                raise ValueError(f"Missing required parameter: {key} (expected keys: {required_keys})")
        
        logger.info(f"[APIFY] fetch_leads input params: {params}")
        
        # Check rate limiting if enabled
        if self.rate_limiter:
            try:
                if not self.rate_limiter.acquire():
                    remaining = self.rate_limiter.get_remaining()
                    error_msg = (
                        f"Rate limit exceeded for Apollo/Apify API. "
                        f"Remaining requests: {remaining}. "
                        f"Try again in {self.rate_limiter.period_seconds} seconds."
                    )
                    logger.warning(
                        f"Rate limit exceeded for Apollo leads fetch: campaign {campaign_id}",
                        extra={
                            'component': 'apollo_service',
                            'rate_limit_exceeded': True,
                            'remaining_requests': remaining,
                            'campaign_id': campaign_id
                        }
                    )
                    return {
                        'count': 0,
                        'errors': [error_msg],
                        'rate_limited': True,
                        'remaining_requests': remaining,
                        'retry_after_seconds': self.rate_limiter.period_seconds
                    }
            except Exception as rate_limit_error:
                # If rate limiter fails (e.g., Redis unavailable), log and continue
                logger.warning(
                    f"Rate limiter error, proceeding without rate limiting: {rate_limit_error}",
                    extra={'component': 'apollo_service', 'rate_limiter_error': str(rate_limit_error)}
                )
        
        try:
            logger.info(f"[START fetch_leads] campaign_id={campaign_id}")

            # --- Apify actor run block ---
            logger.info(f"[BEFORE ApifyClient actor call] actor_id={self.actor_id} with params: {params}")
            
            # Log rate limiting status for monitoring
            if self.rate_limiter:
                remaining_before = self.rate_limiter.get_remaining()
                logger.info(
                    f"Making Apollo API call with rate limiter remaining: {remaining_before}",
                    extra={
                        'component': 'apollo_service',
                        'rate_limiter_remaining_before': remaining_before,
                        'campaign_id': campaign_id
                    }
                )
            
            run = self.apify_client.actor(self.actor_id).call(run_input=params)
            dataset_id = run.get("defaultDatasetId")
            if not dataset_id:
                raise Exception("No dataset ID returned from Apify actor run.")
            logger.info(f"[GOT dataset_id] {dataset_id}")
            results = list(self.apify_client.dataset(dataset_id).iterate_items())
            logger.info(f"[AFTER dataset.iterate_items] got {len(results)} results")

            # Process and save leads using helper
            errors = []
            try:
                lead_stats = self._save_leads_to_db(results, campaign_id, db)
                created_count = lead_stats['created']
                skipped_count = lead_stats['skipped']
                error_count = lead_stats['errors']
                
                # Add summary to response
                if skipped_count > 0:
                    errors.append(f"Skipped {skipped_count} duplicate/invalid emails")
                if error_count > 0:
                    errors.append(f"Encountered {error_count} errors during processing")
                    
            except Exception as e:
                error_msg = f"Error saving leads: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                created_count = 0
                skipped_count = 0
                error_count = 0
            
            # Log rate limiting status after successful call
            if self.rate_limiter:
                remaining_after = self.rate_limiter.get_remaining()
                logger.info(
                    f"Apollo API call successful. Rate limiter remaining: {remaining_after}",
                    extra={
                        'component': 'apollo_service',
                        'rate_limiter_remaining_after': remaining_after,
                        'campaign_id': campaign_id,
                        'leads_fetched': created_count
                    }
                )
            else:
                logger.info(
                    f"Apollo API call successful",
                    extra={
                        'component': 'apollo_service',
                        'campaign_id': campaign_id,
                        'leads_fetched': created_count
                    }
                )
            
            logger.info(f"[AFTER _save_leads_to_db] created_count={created_count}")
            logger.info(f"Leads fetch complete: {created_count} leads created, {len(errors)} errors")
            return {
                'count': created_count,
                'created': created_count,
                'skipped': skipped_count,
                'errors': errors,
                'error_count': error_count,
                'total_processed': len(results) if 'results' in locals() else 0
            }
            
        except Exception as e:
            error_msg = f"Error fetching leads: {str(e)}"
            logger.error(error_msg)
            raise 