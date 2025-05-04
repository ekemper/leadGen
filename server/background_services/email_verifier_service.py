import os
import requests
from server.models.lead import Lead
from server.config.database import db
from sqlalchemy.orm import scoped_session

class EmailVerifierService:
    """Service for verifying emails using MillionVerifier API."""

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('MILLIONVERIFIER_API_KEY')
        self.base_url = 'https://api.millionverifier.com/api/v3'

    def verify_email(self, email):
        """
        Verify an email address using MillionVerifier API.
        Args:
            email (str): The email address to verify.
        Returns:
            dict: The API response as a dictionary.
        """
        params = {
            'api': self.api_key,
            'email': email
        }
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {'result': 'error', 'error': str(e)}

    def verify_emails_for_campaign(self, campaign_id):
        """
        Verify emails for all leads in a given campaign and update their records.
        Args:
            campaign_id (str): The campaign ID to filter leads.
        Returns:
            int: Number of leads processed.
        """
        try:
            leads = db.session.query(Lead).filter_by(campaign_id=campaign_id).all()
            for lead in leads:
                result = self.verify_email(lead.email)
                lead.email_verification = result
            db.session.commit()
            return len(leads)
        finally:
            db.session.remove() 