import os
import requests
from server.models import Campaign, Lead
from server.config.database import db
from server.utils.logging_config import server_logger
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
            server_logger.error(f"Error verifying email {email}: {str(e)}", extra={'component': 'server'})
            return {
                'status': 'error',
                'error': str(e)
            }

    # def verify_emails_for_campaign(self, campaign_id: str) -> int:
        """
        Verify all email addresses for leads in a campaign.
        
        Args:
            campaign_id: ID of the campaign to verify emails for
            
        Returns:
            Number of emails verified
        """
        try:
            # Get campaign
            campaign = Campaign.query.get(campaign_id)
            if not campaign:
                raise ValueError(f"Campaign {campaign_id} not found")

            # Update campaign status
            campaign.update_status(
                CampaignStatus.VERIFYING_EMAILS,
                "Verifying email addresses"
            )

            # Get all leads for the campaign
            leads = Lead.query.filter_by(campaign_id=campaign_id).all()
            server_logger.info(f"Found {len(leads)} leads to verify for campaign {campaign_id}", extra={'component': 'server'})

            verified_count = 0
            errors = []

            for lead in leads:
                try:
                    if not lead.email:
                        continue

                    result = self.verify_email(lead.email)
                    lead.email_verification = result
                    verified_count += 1

                    # Log progress periodically
                    if verified_count % 10 == 0:
                        server_logger.info(f"Verified {verified_count}/{len(leads)} emails for campaign {campaign_id}", extra={'component': 'server'})

                except Exception as e:
                    error_msg = f"Error verifying email for lead {lead.id}: {str(e)}"
                    server_logger.error(error_msg, extra={'component': 'server'})
                    errors.append(error_msg)

            db.session.commit()

            # Update campaign status
            campaign.update_status(
                CampaignStatus.EMAILS_VERIFIED,
                f"Verified {verified_count} emails" + (f" with {len(errors)} errors" if errors else "")
            )

            return verified_count

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error verifying emails for campaign {campaign_id}: {str(e)}"
            server_logger.error(error_msg, extra={'component': 'server'})
            if campaign:
                campaign.update_status(
                    CampaignStatus.FAILED,
                    error=error_msg
                )
            raise 