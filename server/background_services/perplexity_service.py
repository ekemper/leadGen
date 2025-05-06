import os
import requests
from server.models.lead import Lead
from server.config.database import db
from server.utils.logger import logger
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
        """
        if not lead:
            raise ValueError("Lead is required")

        # Map properties from the lead record
        first_name = lead.name.split(' ')[0]
        last_name = ' '.join(lead.name.split(' ')[1:])
        company_name = lead.company_name
        
        # Try to get headline from raw_lead_data or fallback to status
        headline = ''
        if hasattr(lead, 'raw_lead_data') and lead.raw_lead_data:
            headline = lead.raw_lead_data.get('headline')
        if not headline:
            headline = getattr(lead, 'status', '')

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
                logger.info(f"Enriching lead {lead.id} (attempt {attempt + 1}/{self.MAX_RETRIES})")
                response = requests.post(self.API_URL, json=prompt, headers=self.headers, timeout=30)
                response.raise_for_status()
                return response.json()
            except requests.RequestException as e:
                error_msg = f"Perplexity API request failed for lead {lead.id}: {str(e)}"
                logger.error(error_msg)
                if attempt < self.MAX_RETRIES - 1:
                    continue
                return {'error': error_msg}
            except Exception as e:
                error_msg = f"Unexpected error enriching lead {lead.id}: {str(e)}"
                logger.error(error_msg)
                return {'error': error_msg}

    def enrich_leads(self, campaign_id: str) -> Dict[str, Any]:
        """
        Enrich leads for a given campaign_id that passed email verification.
        Args:
            campaign_id (str): The campaign ID to filter leads.
        Returns:
            dict: Results including count of processed leads and any errors.
        """
        if not campaign_id:
            raise ValueError("campaign_id is required")

        try:
            leads = db.session.query(Lead).filter_by(campaign_id=campaign_id).all()
            logger.info(f"Found {len(leads)} leads for campaign {campaign_id}")
            
            # Filter leads that passed email verification
            valid_leads = [lead for lead in leads if lead.email_verification and lead.email_verification.get('result') == 'ok']
            logger.info(f"Found {len(valid_leads)} valid leads for enrichment out of {len(leads)} total")
            
            processed = 0
            errors = []
            
            for lead in valid_leads:
                try:
                    result = self.enrich_lead(lead)
                    if 'error' in result:
                        errors.append(f"Lead {lead.id}: {result['error']}")
                        lead.enrichment_results = {'error': result['error']}
                    else:
                        lead.enrichment_results = result
                        processed += 1
                except Exception as e:
                    error_msg = f"Failed to enrich lead {lead.id}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    lead.enrichment_results = {'error': error_msg}

            try:
                db.session.commit()
                logger.info(f"Successfully enriched {processed} leads for campaign {campaign_id}")
                if errors:
                    logger.warning(f"Completed with {len(errors)} errors: {errors}")
                return {
                    'processed': processed,
                    'errors': errors
                }
            except Exception as e:
                db.session.rollback()
                error_msg = f"Database error while saving enrichment results: {str(e)}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error in enrich_leads: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        finally:
            db.session.remove() 