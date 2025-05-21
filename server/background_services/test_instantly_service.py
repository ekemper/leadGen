import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from dotenv import load_dotenv
load_dotenv()
print("sys.path:", sys.path)
from server.background_services.instantly_service import InstantlyService

def test_instantly_api(campaign_id):
    # Dummy data for testing
    email = "dummy.email@example.com"
    first_name = "Test"
    personalization = "This is a test email copy for Instantly API integration."

    service = InstantlyService()
    response = service.create_lead(
        campaign_id=campaign_id,
        email=email,
        first_name=first_name,
        personalization=personalization
    )
    print("Instantly API response:", response)

if __name__ == "__main__":
    import requests

    url = "https://api.instantly.ai/api/v2/campaigns"
    api_key = os.getenv("INSTANTLY_API_KEY")
    if not api_key:
        print("Error: INSTANTLY_API_KEY environment variable is not set.")
        sys.exit(1)
    payload = {
        "name": "My First Campaign",
        "campaign_schedule": {
            "schedules": [
                {
                    "name": "My Schedule",
                    "timing": {
                        "from": "09:00",
                        "to": "17:00"
                    },
                    "days": {
                        "monday": True,
                        "tuesday": True
                    },
                    "timezone": "Etc/GMT+12"
                }
            ]
        }
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    response = requests.post(url, json=payload, headers=headers)
    try:
        data = response.json()
    except Exception as e:
        print(f"Error parsing response JSON: {e}\nRaw response: {response.text}")
        sys.exit(1)
    print(f'campaign response: {data}')

    if response.status_code != 200 or "id" not in data:
        print(f"Error: Failed to create campaign or missing 'id'. Status: {response.status_code}, Response: {data}")
        sys.exit(1)

    test_instantly_api(data["id"]) 