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
        
        # Create mock rate limiter with timing methods
        self.mock_rate_limiter = Mock(spec=ApiIntegrationRateLimiter)
        self.mock_rate_limiter.max_requests = 50
        self.mock_rate_limiter.period_seconds = 60
        self.mock_rate_limiter.acquire.return_value = True
        self.mock_rate_limiter.get_remaining.return_value = 25
        self.mock_rate_limiter.get_time_since_last_request.return_value = 5.0
        self.mock_rate_limiter.get_last_request_time.return_value = 1609459200.0  # Mock timestamp

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
        mock_response.status_code = 200
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
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Mock the timing method
        self.mock_rate_limiter.get_time_since_last_request.return_value = 5.0
        
        service = PerplexityService(rate_limiter=self.mock_rate_limiter)
        result = service.enrich_lead(self.test_lead)
        
        assert result == {'choices': [{'message': {'content': 'Test enrichment'}}]}
        self.mock_rate_limiter.acquire.assert_called_once()
        # get_remaining is called twice: once during rate limit check and once for logging
        assert self.mock_rate_limiter.get_remaining.call_count == 2
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
        self.mock_rate_limiter.get_time_since_last_request.side_effect = Exception("Redis connection failed")
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {'choices': [{'message': {'content': 'Test enrichment'}}]}
            mock_response.raise_for_status.return_value = None
            mock_response.status_code = 200
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
        successful_response = Mock()
        successful_response.json.return_value = {'choices': [{'message': {'content': 'Success after retries'}}]}
        successful_response.raise_for_status.return_value = None
        successful_response.status_code = 200
        
        mock_post.side_effect = [
            requests.RequestException("Connection error"),
            requests.RequestException("Timeout error"),
            successful_response
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
        result = service._check_rate_limit("test_operation", "test_lead_id", "test_correlation_id", 1)
        assert result is None

    def test_check_rate_limit_allowed(self):
        """Test _check_rate_limit returns None when rate limit allows request."""
        self.mock_rate_limiter.acquire.return_value = True
        self.mock_rate_limiter.get_time_since_last_request.return_value = 5.0
        service = PerplexityService(rate_limiter=self.mock_rate_limiter)
        result = service._check_rate_limit("test_operation", "test_lead_id", "test_correlation_id", 1)
        assert result is None

    def test_check_rate_limit_exceeded(self):
        """Test _check_rate_limit returns error response when rate limit exceeded."""
        self.mock_rate_limiter.acquire.return_value = False
        self.mock_rate_limiter.get_remaining.return_value = 0
        self.mock_rate_limiter.get_time_since_last_request.return_value = 2.0
        
        service = PerplexityService(rate_limiter=self.mock_rate_limiter)
        result = service._check_rate_limit("test_operation", "test_lead_id", "test_correlation_id", 1)
        
        assert result is not None
        assert result['status'] == 'rate_limited'
        assert 'Rate limit exceeded for Perplexity API' in result['error']

    @pytest.mark.skip(reason="Integration test - requires actual Perplexity API token and should not run in CI")
    def test_enrich_lead_integration(self):
        """Integration test with actual Perplexity API (skipped by default)."""
        # This test would require actual API credentials and should only be run manually
        # when testing against the real Perplexity API
        pass

    def test_timing_logging_functionality(self):
        """Test the new timing and logging functionality works correctly."""
        with patch('requests.post') as mock_post:
            # Mock successful API response
            mock_response = Mock()
            mock_response.json.return_value = {'choices': [{'message': {'content': 'Test enrichment'}}]}
            mock_response.raise_for_status.return_value = None
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            # Set up timing mocks
            self.mock_rate_limiter.get_time_since_last_request.return_value = 3.5
            
            service = PerplexityService(rate_limiter=self.mock_rate_limiter)
            
            # Capture log output
            with patch('app.background_services.perplexity_service.logger') as mock_logger:
                result = service.enrich_lead(self.test_lead)
                
                # Verify the result is correct
                assert result == {'choices': [{'message': {'content': 'Test enrichment'}}]}
                
                # Verify timing logging was called
                timing_calls = [call for call in mock_logger.info.call_args_list 
                              if 'perplexity timing test log' in str(call)]
                
                # Should have at least 2 timing logs: Request Attempt and Request Response
                assert len(timing_calls) >= 2
                
                # Check Request Attempt log
                attempt_log = None
                response_log = None
                for call in timing_calls:
                    log_message = call[0][0]  # First positional argument
                    if 'Request Attempt' in log_message:
                        attempt_log = log_message
                    elif 'Request Response' in log_message:
                        response_log = log_message
                
                # Verify Request Attempt log contains required fields
                assert attempt_log is not None
                assert 'correlation_id=' in attempt_log
                assert 'timestamp=' in attempt_log
                assert 'time_since_last_request=3.5' in attempt_log
                assert 'rate_limiter_decision=allowed' in attempt_log
                assert 'rate_limiter_remaining=25' in attempt_log
                assert 'lead_id=test-lead-id' in attempt_log
                assert 'attempt_number=1' in attempt_log
                
                # Verify Request Response log contains required fields
                assert response_log is not None
                assert 'correlation_id=' in response_log
                assert 'response_status=success' in response_log
                assert 'response_time_ms=' in response_log
                assert 'api_response_code=200' in response_log

    def test_timing_logging_without_rate_limiter(self):
        """Test timing logging works correctly without rate limiter."""
        with patch('requests.post') as mock_post:
            # Mock successful API response
            mock_response = Mock()
            mock_response.json.return_value = {'choices': [{'message': {'content': 'Test enrichment'}}]}
            mock_response.raise_for_status.return_value = None
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            service = PerplexityService()  # No rate limiter
            
            # Capture log output
            with patch('app.background_services.perplexity_service.logger') as mock_logger:
                result = service.enrich_lead(self.test_lead)
                
                # Verify the result is correct
                assert result == {'choices': [{'message': {'content': 'Test enrichment'}}]}
                
                # Verify timing logging was called
                timing_calls = [call for call in mock_logger.info.call_args_list 
                              if 'perplexity timing test log' in str(call)]
                
                # Should have at least 2 timing logs: Request Attempt and Request Response
                assert len(timing_calls) >= 2
                
                # Check for no_limiter decision in attempt log
                attempt_log = None
                for call in timing_calls:
                    log_message = call[0][0]
                    if 'Request Attempt' in log_message:
                        attempt_log = log_message
                        break
                
                assert attempt_log is not None
                assert 'rate_limiter_decision=no_limiter' in attempt_log
                assert 'time_since_last_request=None' in attempt_log

    def test_timing_logging_with_rate_limit_exceeded(self):
        """Test timing logging when rate limit is exceeded."""
        # Set up rate limit exceeded
        self.mock_rate_limiter.acquire.return_value = False
        self.mock_rate_limiter.get_remaining.return_value = 0
        self.mock_rate_limiter.get_time_since_last_request.return_value = 1.5
        
        service = PerplexityService(rate_limiter=self.mock_rate_limiter)
        
        # Capture log output
        with patch('app.background_services.perplexity_service.logger') as mock_logger:
            result = service.enrich_lead(self.test_lead)
            
            # Verify rate limited response
            assert result['status'] == 'rate_limited'
            
            # Verify timing logging was called
            timing_calls = [call for call in mock_logger.info.call_args_list 
                          if 'perplexity timing test log' in str(call)]
            
            # Should have 2 timing logs: Request Attempt and Request Response
            assert len(timing_calls) >= 2
            
            # Check for denied decision in attempt log
            attempt_log = None
            response_log = None
            for call in timing_calls:
                log_message = call[0][0]
                if 'Request Attempt' in log_message:
                    attempt_log = log_message
                elif 'Request Response' in log_message:
                    response_log = log_message
            
            assert attempt_log is not None
            assert 'rate_limiter_decision=denied' in attempt_log
            assert 'time_since_last_request=1.5' in attempt_log
            assert 'rate_limiter_remaining=0' in attempt_log
            
            assert response_log is not None
            assert 'response_status=rate_limited' in response_log

    def test_correlation_id_consistency(self):
        """Test that correlation ID is consistent across all logs for a single request."""
        with patch('requests.post') as mock_post:
            # Mock successful API response
            mock_response = Mock()
            mock_response.json.return_value = {'choices': [{'message': {'content': 'Test enrichment'}}]}
            mock_response.raise_for_status.return_value = None
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            service = PerplexityService(rate_limiter=self.mock_rate_limiter)
            
            # Capture log output
            with patch('app.background_services.perplexity_service.logger') as mock_logger:
                result = service.enrich_lead(self.test_lead)
                
                # Extract correlation IDs from all timing logs
                correlation_ids = set()
                timing_calls = [call for call in mock_logger.info.call_args_list 
                              if 'perplexity timing test log' in str(call)]
                
                for call in timing_calls:
                    log_message = call[0][0]
                    # Extract correlation_id from log message
                    import re
                    match = re.search(r'correlation_id=([^,\s]+)', log_message)
                    if match:
                        correlation_ids.add(match.group(1))
                
                # All logs should have the same correlation ID
                assert len(correlation_ids) == 1
                
                # Correlation ID should be a valid UUID format
                correlation_id = list(correlation_ids)[0]
                uuid_pattern = re.compile(
                    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
                    re.IGNORECASE
                )
                assert uuid_pattern.match(correlation_id)

    def test_request_timing_accuracy(self):
        """Test that request timing measurements are reasonable."""
        with patch('requests.post') as mock_post:
            # Mock API response with delay
            def delayed_response(*args, **kwargs):
                import time
                time.sleep(0.1)  # 100ms delay
                response = Mock()
                response.json.return_value = {'choices': [{'message': {'content': 'Test'}}]}
                response.raise_for_status.return_value = None
                response.status_code = 200
                return response
                
            mock_post.side_effect = delayed_response
            
            service = PerplexityService(rate_limiter=self.mock_rate_limiter)
            
            # Capture log output
            with patch('app.background_services.perplexity_service.logger') as mock_logger:
                result = service.enrich_lead(self.test_lead)
                
                # Find response timing log
                timing_calls = [call for call in mock_logger.info.call_args_list 
                              if 'perplexity timing test log - Request Response' in str(call)]
                
                assert len(timing_calls) >= 1
                response_log = timing_calls[0][0][0]
                
                # Extract response time
                import re
                match = re.search(r'response_time_ms=([0-9.]+)', response_log)
                assert match is not None
                
                response_time = float(match.group(1))
                # Should be roughly 100ms (allowing for some variance)
                assert 50 <= response_time <= 200  # 50-200ms range to account for timing variance


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 