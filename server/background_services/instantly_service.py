import os
import requests
from server.utils.logging_config import server_logger

class InstantlyService:
    """Service for integrating with Instantly API to create leads."""
    API_URL = "https://api.instantly.ai/api/v2/leads"

    def __init__(self):
        self.api_key = os.getenv("INSTANTLY_API_KEY")
        if not self.api_key:
            raise ValueError("INSTANTLY_API_KEY environment variable is not set")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def create_lead(self, campaign_id, email, first_name, personalization):
        payload = {
            "campaign": campaign_id,
            "email": email,
            "first_name": first_name,
            "personalization": personalization
        }
        try:
            response = requests.post(self.API_URL, json=payload, headers=self.headers, timeout=10)
            response.raise_for_status()
            server_logger.info(f"Successfully created Instantly lead for {email} in campaign {campaign_id}")
            return response.json()
        except requests.RequestException as e:
            server_logger.error(f"Error creating Instantly lead for {email}: {str(e)}")
            return {"error": str(e), "payload": payload} 