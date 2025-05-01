import os
import requests
import logging
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

class ApolloService:
    """Service for interacting with the Apollo API."""
    
    def __init__(self):
        """Initialize the Apollo service."""
        load_dotenv()
        self.api_token = os.getenv('APIFY_API_TOKEN')
        self.base_url = "https://api.apify.com/v2/acts/supreme_coder~apollo-scraper/runs/last/dataset/items"
        
    def fetch_leads(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch leads from Apollo using the provided parameters and save to file.
        
        Args:
            params (dict): Parameters for the Apollo API request
                - count (int): Number of leads to fetch
                - excludeGuessedEmails (bool): Whether to exclude guessed emails
                - excludeNoEmails (bool): Whether to exclude leads without emails
                - getEmails (bool): Whether to fetch emails
                - searchUrl (str): The Apollo search URL to scrape
            
        Returns:
            dict: Status of the operation
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            response = requests.get(
                self.base_url,
                headers=headers,
                json=params
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Save the results to a file
            output_file = "temp_apollo_leads.json"
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            return {
                "status": "success",
                "message": f"Leads saved to {output_file}",
                "count": len(data) if isinstance(data, list) else 0
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Apollo leads: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
        except Exception as e:
            logger.error(f"Error saving Apollo leads: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            } 