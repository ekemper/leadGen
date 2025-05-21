import os
import requests
from server.utils.logging_config import app_logger

class InstantlyService:
    """Service for integrating with Instantly API to create leads."""
    API_URL = "https://api.instantly.ai/api/v2/leads"
    API_CAMPAIGN_URL = "https://api.instantly.ai/api/v2/campaigns"

    def __init__(self):
        self.api_key = os.getenv("INSTANTLY_API_KEY")
        if not self.api_key:
            raise ValueError("INSTANTLY_API_KEY environment variable is not set")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def create_lead(self, campaign_id, email, first_name, personalization):
        payload = {
            "campaign": campaign_id,
            "email": email,
            "firstName": first_name,
            "personalization": personalization
        }
        try:
            response = requests.post(self.API_URL, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            app_logger.info(f"Successfully created Instantly lead for {email} in campaign {campaign_id}")
            return response.json()
        except requests.RequestException as e:
            app_logger.error(f"Error creating Instantly lead for {email}: {str(e)}")
            return {"error": str(e), "payload": payload}

    def create_campaign(self, name, schedule_name="My Schedule", timing_from="09:00", timing_to="17:00", days=None, timezone="Etc/GMT+12"):
        # Always use only Monday for the days property
        payload = {
            "name": name,
            "campaign_schedule": {
                "schedules": [
                    {
                        "name": schedule_name,
                        "timing": {
                            "from": timing_from,
                            "to": timing_to
                        },
                        "days": {"monday": True},
                        "timezone": timezone
                    }
                ]
            }
        }
        try:
            response = requests.post(self.API_CAMPAIGN_URL, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            app_logger.info(f"Successfully created Instantly campaign '{name}' with response: {data}")
            return data
        except requests.RequestException as e:
            app_logger.error(f"Error creating Instantly campaign '{name}': {str(e)}")
            return {"error": str(e), "payload": payload}

    def get_campaign_analytics_overview(self, campaign_id, start_date=None, end_date=None, campaign_status=None):
        """
        Fetch campaign analytics overview from Instantly API.
        :param campaign_id: The Instantly campaign ID (string)
        :param start_date: Optional start date (YYYY-MM-DD)
        :param end_date: Optional end date (YYYY-MM-DD)
        :param campaign_status: Optional campaign status (string or int)
        :return: dict (API response or error)
        """
        url = "https://api.instantly.ai/api/v2/campaigns/analytics/overview"
        query = {
            "id": campaign_id,
        }
        if start_date:
            query["start_date"] = start_date
        if end_date:
            query["end_date"] = end_date
        if campaign_status is not None:
            query["campaign_status"] = str(campaign_status)
        try:
            response = requests.get(url, headers=self.headers, params=query, timeout=30)
            response.raise_for_status()
            data = response.json()
            app_logger.info(f"Fetched Instantly analytics overview for campaign {campaign_id}: {data}")
            return data
        except requests.RequestException as e:
            app_logger.error(f"Error fetching Instantly analytics overview for campaign {campaign_id}: {str(e)}")
            return {"error": str(e), "query": query} 