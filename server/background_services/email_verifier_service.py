import os
import requests
from server.models import Campaign, Lead
from server.config.database import db
from server.utils.logging_config import setup_logger
from server.models.campaign import CampaignStatus
from typing import Dict, Any, List

# Configure module logger
logger = setup_logger('email_verifier_service')

class EmailVerifierService:
    """Service for verifying email addresses."""
    
    def __init__(self):
        """Initialize the email verifier service."""
        self.api_key = os.getenv('EMAIL_VERIFIER_API_KEY')
        if not self.api_key:
            raise ValueError("EMAIL_VERIFIER_API_KEY environment variable is not set")
        self.base_url = "https://api.email-validator.net/api/verify"

    def verify_email(self, email: str) -> Dict[str, Any]:
        """
        Verify an email address using the email-validator.net API.
        
        Args:
            email: The email address to verify
            
        Returns:
            dict: The verification result
        """
        try:
            params = {
                'EmailAddress': email,
                'APIKey': self.api_key
            }
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error verifying email {email}: {str(e)}", extra={'component': 'server'})
            return {
                'error': str(e),
                'email': email
            }

