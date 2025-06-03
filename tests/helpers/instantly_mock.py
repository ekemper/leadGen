import pytest
from unittest.mock import patch

class DummyInstantlyService:
    def __init__(self, *args, **kwargs):
        pass
    def create_lead(self, *args, **kwargs):
        return {"result": "mocked"}
    def create_campaign(self, *args, **kwargs):
        return {"id": "mocked-campaign-id"}
    def get_campaign_analytics_overview(self, *args, **kwargs):
        return {"analytics": "mocked"}

@pytest.fixture(autouse=True, scope="module")
def mock_instantly_service():
    """Mock InstantlyService for all tests that import this fixture."""
    with patch("app.services.campaign.InstantlyService", DummyInstantlyService):
        yield 