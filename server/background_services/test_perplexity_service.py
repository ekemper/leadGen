import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from dotenv import load_dotenv
load_dotenv()
print("sys.path:", sys.path)

from server.background_services.perplexity_service import PerplexityService
from server.models.lead import Lead


def test_perplexity_api():
    # Dummy data for testing
    lead = Lead(
        id="test-lead-id",
        campaign_id="test-campaign-id",
        first_name="Test",
        last_name="User",
        email="test.user@example.com",
        company="Test Company",
        title="Head of Testing",
        raw_data=None
    )

    service = PerplexityService()
    response = service.enrich_lead(lead)
    print("Perplexity API response:", response)

if __name__ == "__main__":
    api_key = os.getenv("PERPLEXITY_TOKEN")
    if not api_key:
        print("Error: PERPLEXITY_TOKEN environment variable is not set.")
        sys.exit(1)
    test_perplexity_api() 