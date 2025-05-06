import os
import requests
import logging
from server.models.lead import Lead
from server.config.database import db
from typing import Dict, Any, List
from dotenv import load_dotenv
from server.utils.logger import logger
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
        self.base_url = "https://api.apify.com/v2/actor-tasks"
        
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
            # Get campaign
            campaign = Campaign.query.get(campaign_id)
            if not campaign:
                raise ValueError(f"Campaign {campaign_id} not found")

            # Update campaign status
            campaign.update_status(
                CampaignStatus.FETCHING_LEADS,
                "Fetching leads from Apollo"
            )

            # Make API request to Apollo
            response = requests.post(
                f"{self.base_url}/apollo-scraper/runs?token={self.api_token}",
                json=params
            )
            response.raise_for_status()
            
            # Get run ID and wait for completion
            run_id = response.json()['data']['id']
            logger.info(f"Started Apollo scraper run {run_id}")
            
            # Wait for completion and get results
            results = self._wait_for_completion(run_id)
            
            # Process and save leads
            created_count = 0
            errors = []
            
            for result in results:
                try:
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
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            db.session.commit()
            
            # Update campaign status
            campaign.update_status(
                CampaignStatus.LEADS_FETCHED,
                f"Fetched {created_count} leads" + (f" with {len(errors)} errors" if errors else "")
            )
            
            return {
                'count': created_count,
                'errors': errors
            }
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error fetching leads: {str(e)}"
            logger.error(error_msg)
            if campaign:
                campaign.update_status(
                    CampaignStatus.FAILED,
                    error=error_msg
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
        while True:
            response = requests.get(
                f"{self.base_url}/apollo-scraper/runs/{run_id}?token={self.api_token}"
            )
            response.raise_for_status()
            
            status = response.json()['data']['status']
            if status == 'SUCCEEDED':
                # Get results
                results_response = requests.get(
                    f"{self.base_url}/apollo-scraper/runs/{run_id}/dataset/items?token={self.api_token}"
                )
                results_response.raise_for_status()
                return results_response.json()
            elif status in ['FAILED', 'ABORTED']:
                raise Exception(f"Apollo scraper run failed with status: {status}")
            
            # Wait before checking again
            import time
            time.sleep(5) 