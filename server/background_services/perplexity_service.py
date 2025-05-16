import os
import requests
from server.models.lead import Lead
from server.config.database import db
from server.utils.logging_config import app_logger
from typing import Dict, Any, List

class PerplexityService:
    """Service for enriching leads using Perplexity AI or similar."""

    API_URL = "https://api.perplexity.ai/chat/completions"
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds

    def __init__(self):
        self.token = os.getenv("PERPLEXITY_TOKEN")
        if not self.token:
            raise RuntimeError("PERPLEXITY_TOKEN environment variable is not set")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def build_prompt(self, lead: Lead) -> Dict[str, Any]:
        """
        Build a prompt for Perplexity enrichment using lead details.
        Args:
            lead: Lead object
        Returns:
            dict: The prompt JSON with lead details filled in.
        Raises:
            ValueError: If any required prompt variable is missing.
        """
        if not lead:
            raise ValueError("Lead is required")

        # Map properties from the lead record
        first_name = getattr(lead, 'first_name', '')
        last_name = getattr(lead, 'last_name', '')
        # company_name is not a direct field, fallback to company
        company_name = getattr(lead, 'company_name', None) or getattr(lead, 'company', '')

        # Try to get headline from raw_lead_data or fallback to title
        headline = ''
        if hasattr(lead, 'raw_lead_data') and lead.raw_lead_data:
            headline = lead.raw_lead_data.get('headline')
        if not headline:
            headline = getattr(lead, 'title', '')

        # Log the extracted prompt variables
        app_logger.info(f"Prompt variables for lead {getattr(lead, 'id', None)}: first_name='{first_name}', last_name='{last_name}', headline='{headline}', company_name='{company_name}'", extra={'component': 'perplexity'})

        # Check for missing required properties
        missing = []
        if not first_name:
            missing.append('first_name')
        if not last_name:
            missing.append('last_name')
        if not headline:
            missing.append('headline')
        if not company_name:
            missing.append('company_name')
        if missing:
            error_msg = f"Missing required prompt variables: {', '.join(missing)} for lead {getattr(lead, 'id', None)}"
            app_logger.error(error_msg, extra={'component': 'perplexity'})
            # Attach error to job if possible
            enrichment_job_id = getattr(lead, 'enrichment_job_id', None)
            if enrichment_job_id:
                from server.models.job import Job
                from server.models.job_status import JobStatus
                job = Job.query.get(enrichment_job_id)
                if job:
                    job.error_details = {'prompt_error': error_msg, 'missing_fields': missing}
                    job.update_status(JobStatus.FAILED, error_message=error_msg)
                    db.session.commit()
            raise ValueError(error_msg)

        prompt = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [
                {"role": "system", "content": "Be precise and concise."},
                {"role": "user", "content": f"{first_name} {last_name} who is the {headline} at {company_name}"}
            ],
            "temperature": 0.2,
            "top_p": 0.9,
            "search_domain_filter": ["perplexity.ai"],
            "return_images": False,
            "return_related_questions": False,
            "search_recency_filter": "month",
            "top_k": 0,
            "stream": False,
            "presence_penalty": 0,
            "frequency_penalty": 1
        }
        # Log the built prompt
        app_logger.info(f"Built Perplexity prompt for lead {getattr(lead, 'id', None)}: {prompt}", extra={'component': 'perplexity'})
        return prompt

    def enrich_lead(self, lead: Lead) -> Dict[str, Any]:
        """
        Enrich a single lead using Perplexity API.
        Args:
            lead: Lead object to enrich
        Returns:
            dict: Enrichment results
        """
        if not lead:
            raise ValueError("Lead is required")

        prompt = self.build_prompt(lead)
        
        for attempt in range(self.MAX_RETRIES):
            try:
                app_logger.info(f"Enriching lead {lead.id} (attempt {attempt + 1}/{self.MAX_RETRIES})", extra={'component': 'server'})
                response = requests.post(self.API_URL, json=prompt, headers=self.headers, timeout=30)
                response.raise_for_status()
                return response.json()
            except requests.RequestException as e:
                error_msg = f"Perplexity API request failed for lead {lead.id}: {str(e)}"
                app_logger.error(error_msg, extra={'component': 'server'})
                if attempt < self.MAX_RETRIES - 1:
                    continue
                return {'error': error_msg}
            except Exception as e:
                error_msg = f"Unexpected error enriching lead {lead.id}: {str(e)}"
                app_logger.error(error_msg, extra={'component': 'server'})
                return {'error': error_msg} 