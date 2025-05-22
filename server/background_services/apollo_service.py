import os
from apify_client import ApifyClient
from server.models.lead import Lead
from server.config.database import db
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from server.utils.logging_config import setup_logger, ContextLogger
from server.models import Campaign
from server.models.campaign import CampaignStatus
import random
import time
from datetime import datetime
import json
import traceback
import apify_client
from server.background_services.mock_apify_client import MockApifyClient
import logging
import asyncio
from playwright.async_api import async_playwright
from server.utils.error_messages import CAMPAIGN_ERRORS

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

# Configure module logger
logger = setup_logger('apollo_service')

class ApolloService:
    """Service for interacting with the Apollo API."""
    
    def __init__(self):
        """Initialize the Apollo service."""
        load_dotenv()
        self.api_token = os.getenv('APIFY_API_TOKEN')
        if not self.api_token:
            raise ValueError("APIFY_API_TOKEN environment variable is not set")
        # Use mock client if env var is set
        use_mock = os.getenv("USE_APIFY_CLIENT_MOCK", "false").lower() == "true"
        if use_mock:
            self.client = MockApifyClient(self.api_token)
        else:
            self.client = ApifyClient(self.api_token)
        self.actor_id = "code_crafter/apollo-io-scraper"
        # self.actor_id = "supreme_coder/apollo-scraper"
        self.logger = logger

    def _save_leads_to_db(self, results, campaign_id):
        with ContextLogger(self.logger, campaign_id=campaign_id):
            try:
                created_count = 0
                errors = []
                
                for idx, result in enumerate(results):
                    try:
                        self.logger.debug("Creating lead", extra={
                            'metadata': {
                                'email': result.get('email', '[no email]'),
                                'index': idx
                            }
                        })
                        self.logger.debug(f"[LEAD] raw_data: {result}")

                        # Ensure result is a dict and not None
                        if not isinstance(result, dict) or not result:
                            error_msg = f"[LEAD] Lead {idx}: Apify result is not a valid non-empty dict: {result}"
                            self.logger.error(error_msg, extra={'component': 'server'})
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
                        self.logger.info("Lead added to session", extra={
                            'metadata': {'email': lead.email}
                        })
                        created_count += 1
                    except Exception as e:
                        error_msg = f"Error creating lead {idx}: {str(e)}"
                        self.logger.error(error_msg)
                        errors.append(error_msg)
                
                try:
                    db.session.commit()
                    self.logger.info("Leads committed to database", extra={
                        'metadata': {
                            'count': created_count,
                            'campaign_id': campaign_id
                        }
                    })
                except Exception as e:
                    self.logger.error("Database commit failed", exc_info=True)
                    raise
                
                return created_count, errors
            except Exception as e:
                self.logger.error("Failed to save leads", exc_info=True)
                raise

    async def fetch_leads(self, campaign_id: int, params: dict):
        with ContextLogger(self.logger, campaign_id=campaign_id):
            try:
                self.logger.info("Starting leads fetch", extra={
                    'metadata': {'params': params}
                })
                
                # Validate input shape
                required_keys = ['fileName', 'totalRecords', 'url']
                for key in required_keys:
                    if key not in params:
                        raise ValueError(f"Missing required parameter: {key} (expected keys: {required_keys})")
                self.logger.info(f"[APIFY] fetch_leads input params: {params}")
                
                # Get campaign
                campaign = Campaign.query.get(campaign_id)
                self.logger.info(f"[AFTER Campaign.query.get] campaign={campaign}", extra={'component': 'server'})
                if not campaign:
                    self.logger.error(f"Campaign {campaign_id} not found", extra={'component': 'server'})
                    raise ValueError(f"Campaign {campaign_id} not found")

                # Update campaign status to FETCHING_LEADS before fetching
                campaign.update_status(CampaignStatus.FETCHING_LEADS, "Fetching leads from Apollo")
                db.session.commit()

                # --- Apify actor run block ---
                self.logger.info(f"[BEFORE ApifyClient actor call] actor_id={self.actor_id} with params: {params}", extra={'component': 'server'})
                run = self.client.actor(self.actor_id).call(run_input=params)
                dataset_id = run.get("defaultDatasetId")
                if not dataset_id:
                    raise Exception("No dataset ID returned from Apify actor run.")
                self.logger.info(f"[GOT dataset_id] {dataset_id}", extra={'component': 'server'})
                results = list(self.client.dataset(dataset_id).iterate_items())
                self.logger.info(f"[AFTER dataset.iterate_items] got {len(results)} results", extra={'component': 'server'})

                # Process and save leads using helper
                created_count, errors = self._save_leads_to_db(results, campaign_id)
                
                self.logger.info(f"[AFTER _save_leads_to_db] created_count={created_count}", extra={'component': 'server'})
                
                # Update campaign status to indicate leads have been fetched
                self.logger.info(f"[BEFORE campaign.update_status]", extra={'component': 'server'})
                campaign.update_status(
                    CampaignStatus.FETCHING_LEADS,
                    f"Fetched {created_count} leads" + (f" with {len(errors)} errors" if errors else "")
                )
                db.session.commit()
                self.logger.info(f"[AFTER campaign.update_status]", extra={'component': 'server'})
                self.logger.info("Leads fetch complete", extra={
                    'metadata': {
                        'created_count': created_count,
                        'error_count': len(errors)
                    }
                })
                
                return created_count, errors
            except Exception as e:
                db.session.rollback()
                error_msg = f"Error fetching leads: {str(e)}"
                self.logger.error(error_msg, extra={'component': 'server'})
                if 'campaign' in locals() and campaign:
                    campaign.update_status(
                        CampaignStatus.FAILED,
                        error_message=error_msg
                    )
                raise 