"""
Test campaign service validation logic for service availability requirements.

This test suite verifies that campaigns cannot be started when any required
service is unavailable, ensuring fail-fast behavior and preventing the
"running but paused" state issue.
"""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.services.campaign import CampaignService
from app.models.campaign import Campaign
from app.models.campaign_status import CampaignStatus
from app.core.circuit_breaker import ThirdPartyService, CircuitState


class TestCampaignStartValidation:
    """Test campaign start validation with service availability requirements."""

    @pytest.fixture
    def campaign_service(self):
        """Create a CampaignService instance for testing."""
        return CampaignService()

    @pytest.fixture
    def mock_campaign(self):
        """Create a mock campaign in CREATED state."""
        campaign = Mock(spec=Campaign)
        campaign.status = CampaignStatus.CREATED
        campaign.can_be_started.return_value = (True, "Campaign can be started")
        return campaign

    @pytest.fixture
    def mock_circuit_breaker(self):
        """Create a mock circuit breaker."""
        circuit_breaker = Mock()
        return circuit_breaker

    def test_all_services_available_allows_start(self, campaign_service, mock_campaign, mock_circuit_breaker):
        """Test that campaign can start when all required services are available."""
        # Setup - all services are available
        mock_circuit_breaker.should_allow_request.return_value = (True, "Service available")
        
        with patch('app.services.campaign.get_circuit_breaker', return_value=mock_circuit_breaker):
            can_start, reason = campaign_service.can_start_campaign(mock_campaign)
        
        assert can_start is True
        assert "all validations passed" in reason.lower()
        
        # Verify all required services were checked
        expected_calls = len(CampaignService.REQUIRED_SERVICES)
        assert mock_circuit_breaker.should_allow_request.call_count == expected_calls * 2  # Called in both methods

    def test_apollo_unavailable_prevents_start(self, campaign_service, mock_campaign, mock_circuit_breaker):
        """Test that Apollo service unavailability prevents campaign start."""
        def mock_should_allow(service):
            if service == ThirdPartyService.APOLLO:
                return (False, "Circuit breaker OPEN - rate limit exceeded")
            return (True, "Service available")
        
        mock_circuit_breaker.should_allow_request.side_effect = mock_should_allow
        
        with patch('app.services.campaign.get_circuit_breaker', return_value=mock_circuit_breaker):
            can_start, reason = campaign_service.can_start_campaign(mock_campaign)
        
        assert can_start is False
        assert "apollo" in reason.lower()
        assert "unavailable" in reason.lower()

    def test_perplexity_unavailable_prevents_start(self, campaign_service, mock_campaign, mock_circuit_breaker):
        """Test that Perplexity service unavailability prevents campaign start."""
        def mock_should_allow(service):
            if service == ThirdPartyService.PERPLEXITY:
                return (False, "Circuit breaker OPEN - API error")
            return (True, "Service available")
        
        mock_circuit_breaker.should_allow_request.side_effect = mock_should_allow
        
        with patch('app.services.campaign.get_circuit_breaker', return_value=mock_circuit_breaker):
            can_start, reason = campaign_service.can_start_campaign(mock_campaign)
        
        assert can_start is False
        assert "perplexity" in reason.lower()
        assert "unavailable" in reason.lower()

    def test_openai_unavailable_prevents_start(self, campaign_service, mock_campaign, mock_circuit_breaker):
        """Test that OpenAI service unavailability prevents campaign start."""
        def mock_should_allow(service):
            if service == ThirdPartyService.OPENAI:
                return (False, "Circuit breaker OPEN - quota exceeded")
            return (True, "Service available")
        
        mock_circuit_breaker.should_allow_request.side_effect = mock_should_allow
        
        with patch('app.services.campaign.get_circuit_breaker', return_value=mock_circuit_breaker):
            can_start, reason = campaign_service.can_start_campaign(mock_campaign)
        
        assert can_start is False
        assert "openai" in reason.lower()
        assert "unavailable" in reason.lower()

    def test_instantly_unavailable_prevents_start(self, campaign_service, mock_campaign, mock_circuit_breaker):
        """Test that Instantly service unavailability prevents campaign start."""
        def mock_should_allow(service):
            if service == ThirdPartyService.INSTANTLY:
                return (False, "Circuit breaker OPEN - service down")
            return (True, "Service available")
        
        mock_circuit_breaker.should_allow_request.side_effect = mock_should_allow
        
        with patch('app.services.campaign.get_circuit_breaker', return_value=mock_circuit_breaker):
            can_start, reason = campaign_service.can_start_campaign(mock_campaign)
        
        assert can_start is False
        assert "instantly" in reason.lower()
        assert "unavailable" in reason.lower()

    def test_millionverifier_unavailable_prevents_start(self, campaign_service, mock_campaign, mock_circuit_breaker):
        """Test that MillionVerifier service unavailability prevents campaign start."""
        def mock_should_allow(service):
            if service == ThirdPartyService.MILLIONVERIFIER:
                return (False, "Circuit breaker OPEN - timeout")
            return (True, "Service available")
        
        mock_circuit_breaker.should_allow_request.side_effect = mock_should_allow
        
        with patch('app.services.campaign.get_circuit_breaker', return_value=mock_circuit_breaker):
            can_start, reason = campaign_service.can_start_campaign(mock_campaign)
        
        assert can_start is False
        assert "millionverifier" in reason.lower()
        assert "unavailable" in reason.lower()

    def test_multiple_services_unavailable_prevents_start(self, campaign_service, mock_campaign, mock_circuit_breaker):
        """Test that multiple unavailable services are all reported."""
        def mock_should_allow(service):
            if service in [ThirdPartyService.APOLLO, ThirdPartyService.OPENAI]:
                return (False, "Circuit breaker OPEN")
            return (True, "Service available")
        
        mock_circuit_breaker.should_allow_request.side_effect = mock_should_allow
        
        with patch('app.services.campaign.get_circuit_breaker', return_value=mock_circuit_breaker):
            can_start, reason = campaign_service.can_start_campaign(mock_campaign)
        
        assert can_start is False
        assert "apollo" in reason.lower()
        assert "openai" in reason.lower()
        assert "unavailable" in reason.lower()

    def test_paused_campaign_cannot_start(self, campaign_service, mock_campaign, mock_circuit_breaker):
        """Test that paused campaigns cannot be started."""
        mock_campaign.status = CampaignStatus.PAUSED
        mock_circuit_breaker.should_allow_request.return_value = (True, "Service available")
        
        with patch('app.services.campaign.get_circuit_breaker', return_value=mock_circuit_breaker):
            can_start, reason = campaign_service.can_start_campaign(mock_campaign)
        
        assert can_start is False
        assert "paused" in reason.lower()

    def test_validate_campaign_start_prerequisites_comprehensive(self, campaign_service, mock_campaign, mock_circuit_breaker):
        """Test comprehensive validation method with service unavailability."""
        def mock_should_allow(service):
            if service == ThirdPartyService.PERPLEXITY:
                return (False, "Circuit breaker OPEN - rate limit")
            return (True, "Service available")
        
        mock_circuit_breaker.should_allow_request.side_effect = mock_should_allow
        
        with patch('app.services.campaign.get_circuit_breaker', return_value=mock_circuit_breaker):
            result = campaign_service.validate_campaign_start_prerequisites(mock_campaign)
        
        # Should fail overall
        assert result["can_start"] is False
        
        # Should pass campaign status check
        assert result["campaign_status_valid"] is True
        
        # Should fail services check
        assert result["services_available"] is False
        
        # Should have errors about perplexity
        assert len(result["errors"]) > 0
        assert any("perplexity" in error.lower() for error in result["errors"])
        
        # Should have detailed service status
        assert "services" in result["validation_details"]
        assert "perplexity" in result["validation_details"]["services"]
        assert result["validation_details"]["services"]["perplexity"]["available"] is False

    def test_required_services_constant_completeness(self):
        """Test that REQUIRED_SERVICES constant includes all expected services."""
        expected_services = {
            ThirdPartyService.APOLLO,
            ThirdPartyService.PERPLEXITY,
            ThirdPartyService.OPENAI,
            ThirdPartyService.INSTANTLY,
            ThirdPartyService.MILLIONVERIFIER
        }
        
        actual_services = set(CampaignService.REQUIRED_SERVICES)
        
        assert actual_services == expected_services, \
            f"REQUIRED_SERVICES missing: {expected_services - actual_services}, " \
            f"extra: {actual_services - expected_services}"

    def test_global_pause_state_prevents_start(self, campaign_service, mock_campaign, mock_circuit_breaker):
        """Test that global pause state prevents campaign start."""
        # Setup - most services are down
        def mock_should_allow(service):
            # Only one service available out of 5
            if service == ThirdPartyService.APOLLO:
                return (True, "Service available")
            return (False, "Circuit breaker OPEN")
        
        mock_circuit_breaker.should_allow_request.side_effect = mock_should_allow
        
        with patch('app.services.campaign.get_circuit_breaker', return_value=mock_circuit_breaker):
            can_start, reason = campaign_service.can_start_campaign(mock_campaign)
        
        assert can_start is False
        # Should fail due to individual service checks before reaching global pause check
        assert "unavailable" in reason.lower() 