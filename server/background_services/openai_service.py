import os
import json
import requests
from server.models.lead import Lead
from server.config.database import db
from server.utils.logging_config import app_logger
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
        # openai.api_key = self.api_key  # Deprecated in openai>=1.0.0
        self.client = openai.OpenAI(api_key=self.api_key)  # New client instance

    def generate_email_copy(self, lead: Lead, enrichment_data: Dict[str, Any]) -> dict:
        """
        Generate personalized email copy for a lead.
        Args:
            lead: The lead to generate email copy for
            enrichment_data: Additional data about the lead
        Returns:
            The full OpenAI API response (dict)
        """
        try:
            # Extract and log prompt variables
            first_name = getattr(lead, 'first_name', '')
            last_name = getattr(lead, 'last_name', '')
            company_name = getattr(lead, 'company_name', None) or getattr(lead, 'company', '')
            full_name = f"{first_name} {last_name}".strip()
            app_logger.info(f"Email copy prompt vars for lead {getattr(lead, 'id', None)}: first_name='{first_name}', last_name='{last_name}', company_name='{company_name}'", extra={'component': 'OpenAIService'})

            # Validate required fields
            missing = []
            if not first_name:
                missing.append('first_name')
            if not last_name:
                missing.append('last_name')
            if not company_name:
                missing.append('company_name')
            if missing:
                error_msg = f"Missing required prompt variables for email copy: {', '.join(missing)} for lead {getattr(lead, 'id', None)}"
                app_logger.error(error_msg, extra={'component': 'OpenAIService'})
                raise ValueError(error_msg)

            prompt = f"""Write a personalized email to {full_name} at {company_name}.
\nCompany Information:\n{enrichment_data.get('company_description', 'No company description available')}\n\nLead Information:\n- Name: {full_name}\n- Company: {company_name}\n- Role: {enrichment_data.get('role', 'Unknown')}\n- Industry: {enrichment_data.get('industry', 'Unknown')}\n\nAdditional Context:\n{enrichment_data.get('additional_context', 'No additional context available')}\n\nWrite a professional, personalized email that:\n1. Shows understanding of their business\n2. Offers specific value\n3. Has a clear call to action\n4. Is concise and engaging\n\nEmail:"""

            app_logger.info(f"Built email copy prompt for lead {getattr(lead, 'id', None)}: {prompt}", extra={'component': 'OpenAIService'})

            # Call OpenAI API (openai>=1.0.0 interface)
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a professional email copywriter."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )

            return response
        except Exception as e:
            error_msg = f"Error generating email copy for lead {lead.id}: {str(e)}"
            app_logger.error(error_msg, extra={'component': 'OpenAIService'})
            raise 