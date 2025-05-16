import os
from apify_client import ApifyClient
from server.models.lead import Lead
from server.config.database import db
from typing import Dict, Any, List
from dotenv import load_dotenv
from server.utils.logging_config import app_logger
from server.models import Campaign
from server.models.campaign import CampaignStatus
import random
import time
from datetime import datetime
import json
import traceback
import apify_client

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
    """Service for interacting with the Apollo API."""
    
    def __init__(self):
        """Initialize the Apollo service."""
        load_dotenv()
        self.api_token = os.getenv('APIFY_API_TOKEN')
        if not self.api_token:
            raise ValueError("APIFY_API_TOKEN environment variable is not set")
        self.client = ApifyClient(self.api_token)
        self.actor_id = "code_crafter/apollo-io-scraper"
        # self.actor_id = "supreme_coder/apollo-scraper"

    def _save_leads_to_db(self, leads_data: List[Dict[str, Any]], campaign_id: str) -> int:
        """
        Helper to save leads to the database session and commit.
        Returns the number of leads created.
        """
        created_count = 0
        for idx, result in enumerate(leads_data):
            try:
                app_logger.debug(f"[LEAD] Lead {idx}: Creating lead with email '{result.get('email', '[no email]')}' for campaign {campaign_id}")
                app_logger.debug(f"[LEAD] raw_data: {result}")

                # Ensure result is a dict and not None
                if not isinstance(result, dict) or not result:
                    error_msg = f"[LEAD] Lead {idx}: Apify result is not a valid non-empty dict: {result}"
                    app_logger.error(error_msg, extra={'component': 'server'})
                    raise ValueError(error_msg)

                # Map company: prefer organization.name, then organization_name, else ''
                company = ''
                if 'organization' in result and result['organization'] and isinstance(result['organization'], dict):
                    company = result['organization'].get('name', '')
                if not company:
                    company = result.get('organization_name', '')

                lead = Lead(
                    first_name=result.get('first_name', ''),
                    last_name=result.get('last_name', ''),
                    email=result.get('email', ''),
                    phone=result.get('phone', ''),
                    company=company,
                    title=result.get('title', ''),
                    linkedin_url=result.get('linkedin_url', ''),
                    source_url=result.get('source_url', ''),
                    raw_data=result,  # Always a dict here
                    campaign_id=campaign_id
                )
                db.session.add(lead)
                created_count += 1
                app_logger.info(f"[LEAD] Lead {idx}: Added to session (email: {lead.email})")
            except Exception as e:
                error_msg = f"[LEAD] Lead {idx}: Error saving lead (email: {result.get('email', '[no email]')}): {str(e)}"
                app_logger.error(error_msg, extra={'component': 'server'})
        try:
            db.session.commit()
            app_logger.info(f"[LEAD] Committed {created_count} leads to the database for campaign {campaign_id}")
        except Exception as e:
            app_logger.error(f"[LEAD] Database commit failed while saving leads for campaign {campaign_id}: {str(e)}", extra={'component': 'server'})
        return created_count

    def fetch_leads(self, params: Dict[str, Any], campaign_id: str) -> Dict[str, Any]:
        """
        Fetch leads from Apollo and save them to the database.
        Args:
            params: Parameters for the Apollo API (must include fileName, totalRecords, url)
            campaign_id: ID of the campaign to associate leads with
        Returns:
            Dict containing the count of created leads and any errors
        """
        # Validate input shape
        required_keys = ['fileName', 'totalRecords', 'url']
        for key in required_keys:
            if key not in params:
                raise ValueError(f"Missing required parameter: {key} (expected keys: {required_keys})")
        app_logger.info(f"[APIFY] fetch_leads input params: {params}")
        try:
            app_logger.info(f"[START fetch_leads] campaign_id={campaign_id}", extra={'component': 'server'})
            # Get campaign
            campaign = Campaign.query.get(campaign_id)
            app_logger.info(f"[AFTER Campaign.query.get] campaign={campaign}", extra={'component': 'server'})
            if not campaign:
                app_logger.error(f"Campaign {campaign_id} not found", extra={'component': 'server'})
                raise ValueError(f"Campaign {campaign_id} not found")

            # Update campaign status to FETCHING_LEADS before fetching
            campaign.update_status(CampaignStatus.FETCHING_LEADS, "Fetching leads from Apollo")
            db.session.commit()

            # --- Apify actor run block ---
            app_logger.info(f"[BEFORE ApifyClient actor call] actor_id={self.actor_id} with params: {params}", extra={'component': 'server'})
            run = self.client.actor(self.actor_id).call(run_input=params)
            dataset_id = run.get("defaultDatasetId")
            if not dataset_id:
                raise Exception("No dataset ID returned from Apify actor run.")
            app_logger.info(f"[GOT dataset_id] {dataset_id}", extra={'component': 'server'})
            results = list(self.client.dataset(dataset_id).iterate_items())
            app_logger.info(f"[AFTER dataset.iterate_items] got {len(results)} results", extra={'component': 'server'})

            # Process and save leads using helper
            errors = []
            try:
                created_count = self._save_leads_to_db(results, campaign_id)
            except Exception as e:
                error_msg = f"Error saving leads: {str(e)}"
                app_logger.error(error_msg, extra={'component': 'server'})
                errors.append(error_msg)
                created_count = 0
            
            app_logger.info(f"[AFTER _save_leads_to_db] created_count={created_count}", extra={'component': 'server'})
            
            # Update campaign status to indicate leads have been fetched
            app_logger.info(f"[BEFORE campaign.update_status]", extra={'component': 'server'})
            campaign.update_status(
                CampaignStatus.FETCHING_LEADS,
                f"Fetched {created_count} leads" + (f" with {len(errors)} errors" if errors else "")
            )
            db.session.commit()
            app_logger.info(f"[AFTER campaign.update_status]", extra={'component': 'server'})
            app_logger.info(f"Leads fetch complete: {created_count} leads created, {len(errors)} errors", extra={'component': 'server'})
            return {
                'count': created_count,
                'errors': errors
            }
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error fetching leads: {str(e)}"
            app_logger.error(error_msg, extra={'component': 'server'})
            if 'campaign' in locals() and campaign:
                campaign.update_status(
                    CampaignStatus.FAILED,
                    error_message=error_msg
                )
            raise 