import os
import requests
from server.models.lead import Lead
from server.config.database import db

class PerplexityService:
    """Service for enriching leads using Perplexity AI or similar."""

    API_URL = "https://api.perplexity.ai/chat/completions"

    def build_prompt(self, lead):
        """
        Build a prompt for Perplexity enrichment using lead details.
        Args:
            lead: Lead object (SQLAlchemy model or dict)
        Returns:
            dict: The prompt JSON with lead details filled in.
        """
        # Map properties from the lead record
        if isinstance(lead, dict):
            first_name = lead.get('name', '').split(' ')[0]
            last_name = ' '.join(lead.get('name', '').split(' ')[1:])
            company_name = lead.get('company_name', '')
            # Try to get headline from raw_lead_data or fallback to status
            headline = lead.get('raw_lead_data', {}).get('headline') or lead.get('status', '')
        else:
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

    def enrich_leads(self, campaign_id):
        """
        Enrich leads for a given campaign_id that passed email verification.
        Args:
            campaign_id (str): The campaign ID to filter leads.
        Returns:
            list: Leads with enrichment results attached (in 'enrichment_results' field and persisted to DB).
        """
        print(f"PerplexityService.enrich_leads called for campaign_id={campaign_id}")
        token = os.getenv("PERPLEXITY_TOKEN")
        if not token:
            raise RuntimeError("PERPLEXITY_TOKEN environment variable is not set.")
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        try:
            leads = db.session.query(Lead).filter_by(campaign_id=campaign_id).all()
            # Filter leads that passed email verification
            valid_leads = [lead for lead in leads if lead.email_verification and lead.email_verification.get('result') == 'ok']
            print(f"Found {len(valid_leads)} valid leads for enrichment out of {len(leads)} total.")
            enriched_leads = []
            for lead in valid_leads:
                prompt = self.build_prompt(lead)
                try:
                    response = requests.post(self.API_URL, json=prompt, headers=headers, timeout=30)
                    response.raise_for_status()
                    result = response.json()
                    lead.enrichment_results = result
                    db.session.commit()
                except Exception as e:
                    print(f"Perplexity enrichment failed for lead {getattr(lead, 'id', None)}: {e}")
                    lead.enrichment_results = {'error': str(e)}
                    db.session.commit()
                enriched_leads.append(lead)
            return enriched_leads
        finally:
            db.session.remove() 