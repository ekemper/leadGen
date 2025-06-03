# TODO: Temporarily disabled due to import/session issues. Refactor to use app.core.database and app logging, then re-enable.
# import sys
# import os
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
# from dotenv import load_dotenv
# load_dotenv()
# print("sys.path:", sys.path)
#
# from app.background_services.perplexity_service import PerplexityService
# from app.models.lead import Lead
#
# def test_perplexity_api():
#     # Dummy data for testing
#     lead = Lead(
#         id="test-lead-id",
#         campaign_id="test-campaign-id",
#         first_name="Test",
#         last_name="User",
#         email="test.user@example.com",
#         company="Test Company",
#         title="Head of Testing",
#         raw_data=None
#     )
#
#     service = PerplexityService()
#     response = service.enrich_lead(lead)
#     print("Perplexity API response:", response)
#
# if __name__ == "__main__":
#     api_key = os.getenv("PERPLEXITY_TOKEN")
#     if not api_key:
#         print("Error: PERPLEXITY_TOKEN environment variable is not set.")
#         sys.exit(1)
#     test_perplexity_api() 

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from app.background_services.perplexity_service import PerplexityService
from app.models.lead import Lead
from app.core.api_integration_rate_limiter import ApiIntegrationRateLimiter


class TestPerplexityService:
    """Test suite for PerplexityService with rate limiting integration."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Mock the environment variable
        self.env_patcher = patch.dict('os.environ', {'PERPLEXITY_TOKEN': 'test_token'})
        self.env_patcher.start()
        
        # Create test lead
        self.test_lead = Lead(
            id="test-lead-id",
            campaign_id="test-campaign-id",
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            company="Test Company",
            title="Software Engineer",
            raw_data={"headline": "Senior Software Engineer"}
        )
        
        # Create mock rate limiter
        self.mock_rate_limiter = Mock(spec=ApiIntegrationRateLimiter)
        self.mock_rate_limiter.max_requests = 50
        self.mock_rate_limiter.period_seconds = 60
        self.mock_rate_limiter.acquire.return_value = True
        self.mock_rate_limiter.get_remaining.return_value = 25

    def teardown_method(self):
        """Clean up after each test method."""
        if hasattr(self, 'env_patcher'):
            self.env_patcher.stop()

    def test_init_without_rate_limiter(self):
        """Test initialization without rate limiter (backward compatibility)."""
        service = PerplexityService()
        assert service.token == 'test_token'
        assert service.rate_limiter is None
        assert service.headers == {
            "Authorization": "Bearer test_token",
            "Content-Type": "application/json"
        }

    def test_init_with_rate_limiter(self):
        """Test initialization with rate limiter."""
        service = PerplexityService(rate_limiter=self.mock_rate_limiter)
        assert service.token == 'test_token'
        assert service.rate_limiter == self.mock_rate_limiter

    def test_init_missing_token(self):
        """Test initialization raises error when token is missing."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(RuntimeError, match="PERPLEXITY_TOKEN environment variable is not set"):
                PerplexityService()

    def test_build_prompt_success(self):
        """Test successful prompt building."""
        service = PerplexityService()
        result = service.build_prompt(self.test_lead)
        
        assert result["model"] == "llama-3.1-sonar-small-128k-online"
        assert len(result["messages"]) == 2
        assert result["messages"][0]["role"] == "system"
        assert result["messages"][1]["role"] == "user"
        assert "John Doe" in result["messages"][1]["content"]
        assert "Senior Software Engineer" in result["messages"][1]["content"]
        assert "Test Company" in result["messages"][1]["content"]

    def test_build_prompt_fallback_to_title(self):
        """Test prompt building when headline not in raw_data, falls back to title."""
        lead = Lead(
            id="test-lead-id",
            first_name="Jane",
            last_name="Smith",
            company="Test Corp",
            title="Product Manager",
            raw_data=None
        )
        
        service = PerplexityService()
        result = service.build_prompt(lead)
        
        assert "Jane Smith" in result["messages"][1]["content"]
        assert "Product Manager" in result["messages"][1]["content"]

    def test_build_prompt_missing_required_fields(self):
        """Test prompt building raises error when required fields are missing."""
        lead = Lead(id="test-lead-id", first_name="", last_name="", company="", title="")
        
        service = PerplexityService()
        with pytest.raises(ValueError, match="Missing required prompt variables"):
            service.build_prompt(lead)

    def test_build_prompt_none_lead(self):
        """Test prompt building raises error when lead is None."""
        service = PerplexityService()
        with pytest.raises(ValueError, match="Lead is required"):
            service.build_prompt(None)

    @patch('requests.post')
    def test_enrich_lead_success_without_rate_limiter(self, mock_post):
        """Test successful lead enrichment without rate limiter."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {'choices': [{'message': {'content': 'Test enrichment'}}]}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        service = PerplexityService()
        result = service.enrich_lead(self.test_lead)
        
        assert result == {'choices': [{'message': {'content': 'Test enrichment'}}]}
        mock_post.assert_called_once()

    @patch('requests.post')
    def test_enrich_lead_success_with_rate_limiter(self, mock_post):
        """Test successful lead enrichment with rate limiter."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {'choices': [{'message': {'content': 'Test enrichment'}}]}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        service = PerplexityService(rate_limiter=self.mock_rate_limiter)
        result = service.enrich_lead(self.test_lead)
        
        assert result == {'choices': [{'message': {'content': 'Test enrichment'}}]}
        self.mock_rate_limiter.acquire.assert_called_once()
        self.mock_rate_limiter.get_remaining.assert_called_once()
        mock_post.assert_called_once()

    def test_enrich_lead_rate_limit_exceeded(self):
        """Test lead enrichment when rate limit is exceeded."""
        self.mock_rate_limiter.acquire.return_value = False
        self.mock_rate_limiter.get_remaining.return_value = 0
        
        service = PerplexityService(rate_limiter=self.mock_rate_limiter)
        result = service.enrich_lead(self.test_lead)
        
        assert result['status'] == 'rate_limited'
        assert 'Rate limit exceeded for Perplexity API' in result['error']
        assert result['remaining_requests'] == 0
        assert result['retry_after_seconds'] == 60

    def test_enrich_lead_rate_limiter_error_graceful_degradation(self):
        """Test graceful degradation when rate limiter fails."""
        self.mock_rate_limiter.acquire.side_effect = Exception("Redis connection failed")
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {'choices': [{'message': {'content': 'Test enrichment'}}]}
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            service = PerplexityService(rate_limiter=self.mock_rate_limiter)
            result = service.enrich_lead(self.test_lead)
            
            # Should proceed despite rate limiter error
            assert result == {'choices': [{'message': {'content': 'Test enrichment'}}]}
            mock_post.assert_called_once()

    @patch('requests.post')
    def test_enrich_lead_api_error_with_retries(self, mock_post):
        """Test lead enrichment with API errors and retries."""
        # First two calls fail, third succeeds
        mock_post.side_effect = [
            requests.RequestException("Connection error"),
            requests.RequestException("Timeout error"),
            Mock(json=lambda: {'choices': [{'message': {'content': 'Success after retries'}}]}, 
                 raise_for_status=lambda: None)
        ]
        
        service = PerplexityService()
        result = service.enrich_lead(self.test_lead)
        
        assert result == {'choices': [{'message': {'content': 'Success after retries'}}]}
        assert mock_post.call_count == 3

    @patch('requests.post')
    def test_enrich_lead_all_retries_fail(self, mock_post):
        """Test lead enrichment when all retries fail."""
        mock_post.side_effect = requests.RequestException("Persistent error")
        
        service = PerplexityService()
        result = service.enrich_lead(self.test_lead)
        
        assert 'error' in result
        assert 'Perplexity API request failed' in result['error']
        assert mock_post.call_count == 3  # MAX_RETRIES

    @patch('requests.post')
    def test_enrich_lead_unexpected_error(self, mock_post):
        """Test lead enrichment with unexpected error."""
        mock_post.side_effect = Exception("Unexpected error")
        
        service = PerplexityService()
        result = service.enrich_lead(self.test_lead)
        
        assert 'error' in result
        assert 'Unexpected error enriching lead' in result['error']

    def test_enrich_lead_none_lead(self):
        """Test lead enrichment raises error when lead is None."""
        service = PerplexityService()
        with pytest.raises(ValueError, match="Lead is required"):
            service.enrich_lead(None)

    def test_check_rate_limit_no_limiter(self):
        """Test _check_rate_limit returns None when no rate limiter is set."""
        service = PerplexityService()
        result = service._check_rate_limit("test_operation")
        assert result is None

    def test_check_rate_limit_allowed(self):
        """Test _check_rate_limit returns None when rate limit allows request."""
        self.mock_rate_limiter.acquire.return_value = True
        service = PerplexityService(rate_limiter=self.mock_rate_limiter)
        result = service._check_rate_limit("test_operation")
        assert result is None

    def test_check_rate_limit_exceeded(self):
        """Test _check_rate_limit returns error response when rate limit exceeded."""
        self.mock_rate_limiter.acquire.return_value = False
        self.mock_rate_limiter.get_remaining.return_value = 0
        
        service = PerplexityService(rate_limiter=self.mock_rate_limiter)
        result = service._check_rate_limit("test_operation")
        
        assert result is not None
        assert result['status'] == 'rate_limited'
        assert 'Rate limit exceeded for Perplexity API' in result['error']

    @pytest.mark.skip(reason="Integration test - requires actual Perplexity API token and should not run in CI")
    def test_enrich_lead_integration(self):
        """Integration test with actual Perplexity API (skipped by default)."""
        # This test would require actual API credentials and should only be run manually
        # when testing against the real Perplexity API
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 