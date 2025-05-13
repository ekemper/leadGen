import os
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

    data = response.json()
    print(f'campaign response: {data}')

    test_instantly_api(data["id"]) 