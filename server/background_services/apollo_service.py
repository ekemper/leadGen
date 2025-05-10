import os
import requests
from server.models.lead import Lead
from server.config.database import db
from typing import Dict, Any, List
from dotenv import load_dotenv
from server.utils.logging_config import server_logger
from server.models import Campaign
from server.models.campaign import CampaignStatus

class ApolloService:
    """Service for interacting with the Apollo API."""
    
    def __init__(self):
        """Initialize the Apollo service."""
        load_dotenv()
        self.api_token = os.getenv('APIFY_API_TOKEN')
        if not self.api_token:
            raise ValueError("APIFY_API_TOKEN environment variable is not set")
        self.base_url = "https://api.apify.com/v2/acts/supreme_coder~apollo-scraper"


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

            server_logger.info(f"[BEFORE Apollo API POST] {self.base_url}/runs?token=*** with params: {params}", extra={'component': 'server'})
            response = requests.post(
                f"{self.base_url}/runs?token={self.api_token}",
                json=params
            )
            server_logger.info(f"[AFTER Apollo API POST] status={response.status_code}", extra={'component': 'server'})
            response.raise_for_status()
            server_logger.info(f"[AFTER response.raise_for_status]", extra={'component': 'server'})
            run_id = response.json()['data']['id']
            server_logger.info(f"[GOT run_id] {run_id}", extra={'component': 'server'})
            
            # Wait for completion and get results
            server_logger.info(f"[BEFORE _wait_for_completion] run_id={run_id}", extra={'component': 'server'})
            results = self._wait_for_completion(run_id)
            server_logger.info(f"[AFTER _wait_for_completion] got {len(results)} results", extra={'component': 'server'})
            
            # Process and save leads
            created_count = 0
            errors = []
            
            for result in results:
                try:
                    server_logger.debug(f"Processing lead result: {result}", extra={'component': 'server'})
                    lead = Lead(
                        name=result.get('name', ''),
                        email=result.get('email', ''),
                        company_name=result.get('company', ''),
                        phone=result.get('phone', ''),
                        campaign_id=campaign_id,
                        raw_lead_data=result
                    )
                    db.session.add(lead)
                    created_count += 1
                except Exception as e:
                    error_msg = f"Error saving lead: {str(e)}"
                    server_logger.error(error_msg, extra={'component': 'server'})
                    errors.append(error_msg)
            
            server_logger.info(f"[BEFORE db.session.commit] created_count={created_count}", extra={'component': 'server'})
            db.session.commit()
            server_logger.info(f"[AFTER db.session.commit]", extra={'component': 'server'})
            
            # Update campaign status
            server_logger.info(f"[BEFORE campaign.update_status]", extra={'component': 'server'})
            campaign.update_status(
                CampaignStatus.LEADS_FETCHED,
                f"Fetched {created_count} leads" + (f" with {len(errors)} errors" if errors else "")
            )
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

    def _wait_for_completion(self, run_id: str) -> List[Dict[str, Any]]:
        """
        Wait for an Apollo scraper run to complete and return results.
        
        Args:
            run_id: ID of the Apollo scraper run
            
        Returns:
            List of lead data dictionaries
        """
        import time
        server_logger.info(f"[START _wait_for_completion] run_id={run_id}", extra={'component': 'server'})
        while True:
            status_url = f"{self.base_url}/runs/{run_id}?token={self.api_token}"
            server_logger.info(f"[BEFORE requests.get status_url] {status_url}", extra={'component': 'server'})
            response = requests.get(status_url)
            server_logger.info(f"[AFTER requests.get status_url] status={response.status_code}", extra={'component': 'server'})
            response.raise_for_status()
            server_logger.info(f"[AFTER response.raise_for_status status_url]", extra={'component': 'server'})
            status = response.json()['data']['status']
            server_logger.info(f"[GOT status] {status}", extra={'component': 'server'})
            if status == 'SUCCEEDED':
                results_url = f"{self.base_url}/runs/{run_id}/dataset/items?token={self.api_token}"
                server_logger.info(f"[BEFORE requests.get results_url] {results_url}", extra={'component': 'server'})
                # --- Retry logic for 404 on dataset fetch ---
                max_retries = 3
                for attempt in range(1, max_retries + 1):
                    results_response = requests.get(results_url)
                    server_logger.info(f"[AFTER requests.get results_url] status={results_response.status_code} (attempt {attempt})", extra={'component': 'server'})
                    if results_response.status_code == 404:
                        server_logger.warning(
                            f"Apollo run {run_id} SUCCEEDED but dataset not found (404) at {results_url} (attempt {attempt}/{max_retries})",
                            extra={'component': 'server'}
                        )
                        if attempt < max_retries:
                            time.sleep(2)  # Wait before retrying
                            continue
                        else:
                            server_logger.error(f"Dataset still not found after {max_retries} attempts. Returning empty list.", extra={'component': 'server'})
                            return []
                    else:
                        break  # Exit retry loop if not 404
                # --- End retry logic ---
                results_response.raise_for_status()
                server_logger.info(f"[AFTER results_response.raise_for_status]", extra={'component': 'server'})
                server_logger.debug(f"Apollo run results: {results_response.text}", extra={'component': 'server'})
                return results_response.json()
            elif status in ['FAILED', 'ABORTED']:
                server_logger.error(f"Apollo scraper run {run_id} failed with status: {status}", extra={'component': 'server'})
                raise Exception(f"Apollo scraper run failed with status: {status}")
            
            # Wait before checking again
            time.sleep(5) 