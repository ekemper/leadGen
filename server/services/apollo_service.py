import os
import requests
import logging
from models import Lead
from config.database import db
from typing import Dict, Any
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
        
    def fetch_leads(self, params: Dict[str, Any], campaign_id=None) -> Dict[str, Any]:
        """
        Fetch leads from Apollo using the provided parameters and save to the database.
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

            created_leads = []
            for lead_data in data:
                company_name = ''
                company_field = lead_data.get('company', '')
                if isinstance(company_field, dict):
                    company_name = company_field.get('companyName', '')
                elif isinstance(company_field, str):
                    company_name = company_field
                lead = Lead(
                    name=lead_data.get('name', ''),
                    email=lead_data.get('email', ''),
                    company_name=company_name,
                    phone=lead_data.get('phone', ''),
                    status=lead_data.get('status', 'new'),
                    source=lead_data.get('source', 'apollo'),
                    notes=lead_data.get('notes', ''),
                    campaign_id=campaign_id,
                    raw_lead_data=lead_data
                )
                db.session.add(lead)
                created_leads.append(lead)
            db.session.commit()

            return {
                "status": "success",
                "message": f"{len(created_leads)} leads saved to the database",
                "count": len(created_leads),
                "leads": [l.to_dict() for l in created_leads]
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