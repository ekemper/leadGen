import os
import json
import requests
from server.models.lead import Lead
from server.config.database import db
from server.utils.logging_config import server_logger, combined_logger
from typing import Dict, Any, Optional
from server.models import Campaign
from server.models.campaign import CampaignStatus
import openai

class OpenAIService:
    """
    Service for generating email copy using OpenAI's API.
    """

    API_URL = "https://api.openai.com/v1/chat/completions"
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        openai.api_key = self.api_key

    def generate_email_copy(self, lead: Lead, enrichment_data: Dict[str, Any]) -> str:
        """
        Generate personalized email copy for a lead.
        
        Args:
            lead: The lead to generate email copy for
            enrichment_data: Additional data about the lead
            
        Returns:
            Generated email copy
        """
        try:
            # Construct prompt
            prompt = f"""Write a personalized email to {lead.name} at {lead.company_name}.

Company Information:
{enrichment_data.get('company_description', 'No company description available')}

Lead Information:
- Name: {lead.name}
- Company: {lead.company_name}
- Role: {enrichment_data.get('role', 'Unknown')}
- Industry: {enrichment_data.get('industry', 'Unknown')}

Additional Context:
{enrichment_data.get('additional_context', 'No additional context available')}

Write a professional, personalized email that:
1. Shows understanding of their business
2. Offers specific value
3. Has a clear call to action
4. Is concise and engaging

Email:"""

            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a professional email copywriter."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            error_msg = f"Error generating email copy for lead {lead.id}: {str(e)}"
            server_logger.error(error_msg, extra={'component': 'OpenAIService'})
            raise

    def generate_email_copies_for_campaign(self, campaign_id: str) -> int:
        """
        Generate email copies for all leads in a campaign.
        
        Args:
            campaign_id: ID of the campaign to generate emails for
            
        Returns:
            Number of emails generated
        """
        try:
            # Get campaign
            campaign = Campaign.query.get(campaign_id)
            if not campaign:
                raise ValueError(f"Campaign {campaign_id} not found")

            # Update campaign status
            campaign.update_status(
                CampaignStatus.GENERATING_EMAILS,
                "Generating personalized email copy"
            )

            # Get all leads for the campaign
            leads = Lead.query.filter_by(campaign_id=campaign_id).all()
            server_logger.info(f"Found {len(leads)} leads to generate emails for campaign {campaign_id}", extra={'component': 'OpenAIService'})

            generated_count = 0
            errors = []

            for lead in leads:
                try:
                    if not lead.enrichment_results:
                        continue

                    email_copy = self.generate_email_copy(lead, lead.enrichment_results)
                    lead.email_copy = email_copy
                    generated_count += 1

                    # Log progress periodically
                    if generated_count % 10 == 0:
                        server_logger.info(f"Generated {generated_count}/{len(leads)} emails for campaign {campaign_id}", extra={'component': 'OpenAIService'})

                except Exception as e:
                    error_msg = f"Error generating email for lead {lead.id}: {str(e)}"
                    server_logger.error(error_msg, extra={'component': 'OpenAIService'})
                    errors.append(error_msg)

            db.session.commit()

            # Update campaign status
            campaign.update_status(
                CampaignStatus.COMPLETED,
                f"Generated {generated_count} emails" + (f" with {len(errors)} errors" if errors else "")
            )

            return generated_count

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error generating emails for campaign {campaign_id}: {str(e)}"
            server_logger.error(error_msg, extra={'component': 'OpenAIService'})
            if campaign:
                campaign.update_status(
                    CampaignStatus.FAILED,
                    error=error_msg
                )
            raise 