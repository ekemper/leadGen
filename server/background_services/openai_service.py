import os
import json
import requests
from server.models.lead import Lead
from server.config.database import db

class OpenAIService:
    """
    Service for generating email copy using OpenAI's API.
    """

    API_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set.")

    def generate_email_copy(self, lead, enrichment_results):
        """
        Generate a personalized email opener for a lead using OpenAI.

        Args:
            lead: Lead object or dict
            enrichment_results: dict or str (from Perplexity enrichment)
        Returns:
            str: The generated email opener (icebreaker)
        """
        # Extract lead info
        if isinstance(lead, dict):
            name = lead.get('name', '')
            company = lead.get('company_name', '')
        else:
            name = lead.name
            company = lead.company_name

        enrichment_summary = enrichment_results if isinstance(enrichment_results, str) else str(enrichment_results)

        system_prompt = (
            "You are a professional cold email copywriter. "
            "Your objective is to write highly personalized email openers using the information you're given."
        )

        user_prompt = f"""
            <prompt>
            <task>Create a personalized email opener</task>
            <input>
                <summary>{enrichment_summary}</summary>
            </input>
            <guidelines>
                <constraint>Keep it under 20 words</constraint>
                <constraint>Craft a unique message that is specific</constraint>
                <constraint>Find any plausible connection wherever possible</constraint>
                <constraint>End the icebreaker with the one-line phrase \"thought I'd reach out.\"</constraint>
                <constraint>Don't use overly excited tones of voice with exclamation points</constraint>
            </guidelines>
            <tone>stoic and casual</tone>
            <format>
                <output_type>JSON</output_type>
                <json_format>Valid JSON with proper line breaks</json_format>
            </format>
            <example>
                <opener>Hey Amy,\n\nCan deeply relate to your mission of building a calm company culture and focusing on passion that you posted about. Thought I'd reach out.</opener>
            </example>
            </prompt>
            """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7
        }

        response = requests.post(self.API_URL, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content'].strip()

        # Try to parse the JSON output for the icebreaker
        try:
            opener_json = json.loads(content)
            return (
                opener_json.get('icebreaker') or
                opener_json.get('opener') or
                content
            )
        except Exception:
            return content

    def generate_email_copies_for_campaign(self, campaign_id):
        """
        For a given campaign_id, generate and persist email copy for all leads with enrichment_results.
        Args:
            campaign_id (str): The campaign ID to filter leads.
        Returns:
            int: Number of leads updated
        """
        print(f"OpenAIService.generate_email_copies_for_campaign called for campaign_id={campaign_id}")
        try:
            leads = db.session.query(Lead).filter(
                Lead.campaign_id == campaign_id,
                Lead.enrichment_results.isnot(None)
            ).all()
            print(f"Found {len(leads)} leads with enrichment_results for campaign {campaign_id}.")
            count = 0
            for lead in leads:
                try:
                    # Save the full OpenAI response (parsed JSON or raw content)
                    response_content = self._get_full_openai_response(lead, lead.enrichment_results)
                    lead.email_copy = response_content
                    db.session.commit()
                    count += 1
                except Exception as e:
                    print(f"OpenAI email copy generation failed for lead {lead.id}: {e}")
            return count
        finally:
            db.session.remove()

    def _get_full_openai_response(self, lead, enrichment_results):
        """
        Helper to get the full OpenAI response (parsed JSON or raw content) for saving.
        """
        # Extract lead info
        if isinstance(lead, dict):
            name = lead.get('name', '')
            company = lead.get('company_name', '')
        else:
            name = lead.name
            company = lead.company_name

        enrichment_summary = enrichment_results if isinstance(enrichment_results, str) else str(enrichment_results)

        system_prompt = (
            "You are a professional cold email copywriter. "
            "Your objective is to write highly personalized email openers using the information you're given."
        )

        user_prompt = f"""
<prompt>
  <task>Create a personalized email opener</task>
  <input>
    <summary>{enrichment_summary}</summary>
  </input>
  <guidelines>
    <constraint>Keep it under 20 words</constraint>
    <constraint>Craft a unique message that is specific</constraint>
    <constraint>Find any plausible connection wherever possible</constraint>
    <constraint>End the icebreaker with the one-line phrase \"thought I'd reach out.\"</constraint>
    <constraint>Don't use overly excited tones of voice with exclamation points</constraint>
  </guidelines>
  <tone>stoic and casual</tone>
  <format>
    <output_type>JSON</output_type>
    <json_format>Valid JSON with proper line breaks</json_format>
  </format>
  <example>
    <opener>Hey Amy,\n\nCan deeply relate to your mission of building a calm company culture and focusing on passion that you posted about. Thought I'd reach out.</opener>
  </example>
</prompt>
"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7
        }

        print(f' ----> making the request to openai: {data}')

        response = requests.post(self.API_URL, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content'].strip()
        # Try to parse JSON, but fallback to raw content
        try:
            return json.loads(content)
        except Exception:
            return content 