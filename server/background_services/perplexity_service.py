import os
import requests
from server.models.lead import Lead
from server.config.database import db
from server.utils.logging_config import setup_logger
from typing import Dict, Any, List

# Configure module logger
logger = setup_logger('perplexity_service')

class PerplexityService:
    """Service for enriching leads using Perplexity API."""

    API_URL = "https://api.perplexity.ai/chat/completions"
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds

    def __init__(self):
        """Initialize the Perplexity service."""
        self.api_key = os.getenv('PERPLEXITY_API_KEY')
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY environment variable is not set")
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.logger = logger

    def _build_prompt(self, lead) -> str:
        """Build the prompt for lead enrichment."""
        try:
            # Extract lead information
            first_name = lead.first_name or ''
            last_name = lead.last_name or ''
            headline = lead.title or ''
            company_name = lead.company or ''
            
            # Log prompt variables
            self.logger.info(
                f"Prompt variables for lead {getattr(lead, 'id', None)}: "
                f"first_name='{first_name}', last_name='{last_name}', "
                f"headline='{headline}', company_name='{company_name}'",
                extra={'component': 'perplexity'}
            )
            
            # Validate required fields
            missing = []
            if not first_name:
                missing.append('first_name')
            if not last_name:
                missing.append('last_name')
            if not company_name:
                missing.append('company_name')
            if missing:
                error_msg = f"Missing required prompt variables: {', '.join(missing)}"
                self.logger.error(error_msg, extra={'component': 'perplexity'})
                raise ValueError(error_msg)
            
            # Build prompt
            prompt = f"""
            Research {first_name} {last_name} who works as {headline} at {company_name}.
            
            Focus on:
            1. Their professional background and achievements
            2. Their current role and responsibilities
            3. The company's business model and market position
            4. Recent company news or developments
            5. Industry trends affecting their business
            
            Format the response as a structured JSON with these keys:
            - background: Professional history and achievements
            - current_role: Details about their position
            - company_info: Company overview and market position
            - recent_developments: Latest news about them or their company
            - industry_insights: Relevant industry trends
            """
            
            self.logger.info(f"Built Perplexity prompt for lead {getattr(lead, 'id', None)}: {prompt}", extra={'component': 'perplexity'})
            return prompt
            
        except Exception as e:
            self.logger.error(f"Error building prompt: {str(e)}", exc_info=True)
            raise

    def enrich_lead(self, lead) -> Dict[str, Any]:
        """Enrich a lead with additional information."""
        for attempt in range(self.MAX_RETRIES):
            try:
                self.logger.info(f"Enriching lead {lead.id} (attempt {attempt + 1}/{self.MAX_RETRIES})", extra={'component': 'server'})
                
                prompt = self._build_prompt(lead)
                response = requests.post(
                    self.base_url,
                    headers=self.headers,
                    json={
                        "model": "mixtral-8x7b-instruct",
                        "messages": [{"role": "user", "content": prompt}]
                    }
                )
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                error_msg = f"API request failed (attempt {attempt + 1}/{self.MAX_RETRIES}): {str(e)}"
                self.logger.error(error_msg, extra={'component': 'server'})
                if attempt == self.MAX_RETRIES - 1:
                    error_msg = f"Max retries ({self.MAX_RETRIES}) exceeded: {str(e)}"
                    self.logger.error(error_msg, extra={'component': 'server'})
                    return {'error': error_msg} 