import os
import requests
from server.models import Campaign, Lead
from server.config.database import db
from server.utils.logging_config import app_logger
from server.models.campaign import CampaignStatus
from typing import Dict, Any, List

class EmailVerifierService:
    """Service for verifying emails using MillionVerifier API."""

    def __init__(self):
        self.api_key = os.getenv('MILLIONVERIFIER_API_KEY')
        if not self.api_key:
            raise ValueError("MILLIONVERIFIER_API_KEY environment variable is not set")
        self.base_url = "https://api.millionverifier.com/api/v3/"
        self.max_retries = 3
        self.retry_delay = 1  # seconds

    def verify_email(self, email: str) -> Dict[str, Any]:
        """
        Verify a single email address.
        
        Args:
            email: The email address to verify
            
        Returns:
            Dict containing verification results
        """
        try:
            response = requests.get(
                f"{self.base_url}?api={self.api_key}&email={email}"
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            app_logger.error(f"Error verifying email {email}: {str(e)}", extra={'component': 'server'})
            return {
                'status': 'error',
                'error': str(e)
            }

