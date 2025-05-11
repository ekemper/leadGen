import os
from apify_client import ApifyClient
from server.models.lead import Lead
from server.config.database import db
from typing import Dict, Any, List
from dotenv import load_dotenv
from server.utils.logging_config import server_logger
from server.models import Campaign
from server.models.campaign import CampaignStatus
import random
import time

class ApolloService:
    """Service for interacting with the Apollo API."""
    
    def __init__(self):
        """Initialize the Apollo service."""
        load_dotenv()
        self.api_token = os.getenv('APIFY_API_TOKEN')
        if not self.api_token:
            raise ValueError("APIFY_API_TOKEN environment variable is not set")
        self.client = ApifyClient(self.api_token)
        self.actor_id = "supreme_coder/apollo-scraper"

    def _save_leads_to_db(self, leads_data: List[Dict[str, Any]], campaign_id: str) -> int:
        """
        Helper to save leads to the database session and commit.
        Returns the number of leads created.
        """
        created_count = 0
        for idx, result in enumerate(leads_data):
            try:
                server_logger.debug(f"[LEAD {idx}] Attempting to create Lead with data: {result}", extra={'component': 'server'})
                lead = Lead(
                    first_name=result.get('first_name', ''),
                    last_name=result.get('last_name', ''),
                    email=result.get('email', ''),
                    phone=result.get('phone', ''),
                    company=result.get('company', ''),
                    title=result.get('title', ''),
                    linkedin_url=result.get('linkedin_url', ''),
                    source_url=result.get('source_url', ''),
                    raw_data=result.get('raw_data', {}),
                    campaign_id=campaign_id
                )
                db.session.add(lead)
                created_count += 1
                server_logger.info(f"[LEAD {idx}] Lead added to session: {lead}", extra={'component': 'server'})
            except Exception as e:
                error_msg = f"[LEAD {idx}] Error saving lead: {str(e)}"
                server_logger.error(error_msg, extra={'component': 'server'})
        try:
            db.session.commit()
            server_logger.info(f"db.session.commit() called. {created_count} leads should be persisted.", extra={'component': 'server'})
        except Exception as e:
            server_logger.error(f"Error during db.session.commit: {str(e)}", extra={'component': 'server'})
        return created_count

    def fetch_leads(self, params: Dict[str, Any], campaign_id: str) -> Dict[str, Any]:
        """
        Fetch leads from Apollo and save them to the database.
        Args:
            params: Parameters for the Apollo API
            campaign_id: ID of the campaign to associate leads with
        Returns:
            Dict containing the count of created leads and any errors
        """
        try:
            server_logger.info(f"[START fetch_leads] campaign_id={campaign_id}", extra={'component': 'server'})
            # Get campaign
            campaign = Campaign.query.get(campaign_id)
            server_logger.info(f"[AFTER Campaign.query.get] campaign={campaign}", extra={'component': 'server'})
            if not campaign:
                server_logger.error(f"Campaign {campaign_id} not found", extra={'component': 'server'})
                raise ValueError(f"Campaign {campaign_id} not found")

            # Update campaign status to FETCHING_LEADS before fetching
            campaign.update_status(CampaignStatus.FETCHING_LEADS, "Fetching leads from Apollo")
            db.session.commit()

            # --- BEGIN: Dummy leads block ---
            # Commenting out Apify client code
            # server_logger.info(f"[BEFORE ApifyClient actor call] actor_id={self.actor_id} with params: {params}", extra={'component': 'server'})
            # run = self.client.actor(self.actor_id).call(run_input=params)
            # dataset_id = run.get("defaultDatasetId")
            # if not dataset_id:
            #     raise Exception("No dataset ID returned from Apify actor run.")
            # server_logger.info(f"[GOT dataset_id] {dataset_id}", extra={'component': 'server'})
            # results = list(self.client.dataset(dataset_id).iterate_items())
            # server_logger.info(f"[AFTER dataset.iterate_items] got {len(results)} results", extra={'component': 'server'})

            # Create 10 dummy leads
            results = []
            for i in range(10):
                results.append({
                    'first_name': 'Edward',
                    'last_name': 'Kemper',
                    'email': 'edwardkemper@gmail.com',
                    'phone': f'+1-555-000{i:03d}',
                    'company': f'DummyCompany{i}',
                    'title': f'DummyTitle{i}',
                    'linkedin_url': f'https://linkedin.com/in/dummy{i}',
                    'source_url': f'https://source.example.com/lead/{i}',
                    'raw_data': {'source': 'dummy', 'index': i}
                })
            server_logger.info(f"[DUMMY MODE] Generated {len(results)} dummy leads", extra={'component': 'server'})
            # --- END: Dummy leads block ---

            # Process and save leads using helper
            errors = []
            try:
                created_count = self._save_leads_to_db(results, campaign_id)
            except Exception as e:
                error_msg = f"Error saving leads: {str(e)}"
                server_logger.error(error_msg, extra={'component': 'server'})
                errors.append(error_msg)
                created_count = 0
            
            server_logger.info(f"[AFTER _save_leads_to_db] created_count={created_count}", extra={'component': 'server'})
            
            # Update campaign status to indicate leads have been fetched
            server_logger.info(f"[BEFORE campaign.update_status]", extra={'component': 'server'})
            campaign.update_status(
                CampaignStatus.FETCHING_LEADS,
                f"Fetched {created_count} leads" + (f" with {len(errors)} errors" if errors else "")
            )
            db.session.commit()
            server_logger.info(f"[AFTER campaign.update_status]", extra={'component': 'server'})
            server_logger.info(f"Leads fetch complete: {created_count} leads created, {len(errors)} errors", extra={'component': 'server'})
            return {
                'count': created_count,
                'errors': errors
            }
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error fetching leads: {str(e)}"
            server_logger.error(error_msg, extra={'component': 'server'})
            if 'campaign' in locals() and campaign:
                campaign.update_status(
                    CampaignStatus.FAILED,
                    error_message=error_msg
                )
            raise 