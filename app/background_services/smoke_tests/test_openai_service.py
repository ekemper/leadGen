"""
Tests for OpenAIService with Rate Limiting Integration

This test suite validates the OpenAIService functionality including:
- Backward compatibility for existing usage patterns
- Rate limiting integration and behavior
- Error handling and graceful degradation
- OpenAI API response handling and email copy generation
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.background_services.openai_service import OpenAIService
from app.core.api_integration_rate_limiter import ApiIntegrationRateLimiter
from app.models import Lead
from app.core.config import settings

class TestOpenAIService:
    """Test suite for OpenAIService."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Mock the environment variable
        os.environ['OPENAI_API_KEY'] = 'test-api-key'
        
    def teardown_method(self):
        """Cleanup after each test method."""
        if 'OPENAI_API_KEY' in os.environ:
            del os.environ['OPENAI_API_KEY']

    def test_backward_compatibility_initialization(self):
        """Test that OpenAIService can still be initialized without rate limiter."""
        with patch('app.background_services.openai_service.OpenAI') as mock_openai:
            service = OpenAIService()
            
            assert service.rate_limiter is None
            mock_openai.assert_called_once_with(api_key='test-api-key')
        
    def test_rate_limiter_initialization(self):
        """Test that OpenAIService can be initialized with rate limiter."""
        with patch('app.background_services.openai_service.OpenAI') as mock_openai:
            mock_redis = Mock()
            # Use configuration settings instead of hardcoded values
            rate_limiter = ApiIntegrationRateLimiter(
                mock_redis, 'OpenAI', 
                settings.OPENAI_RATE_LIMIT_REQUESTS, 
                settings.OPENAI_RATE_LIMIT_PERIOD
            )
            
            service = OpenAIService(rate_limiter=rate_limiter)
            
            assert service.rate_limiter is rate_limiter
            mock_openai.assert_called_once_with(api_key='test-api-key')
        
    def test_missing_api_key_raises_error(self):
        """Test that missing API key raises ValueError."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable is not set"):
                OpenAIService()

    def create_mock_lead(self, **kwargs):
        """Create a mock lead with default values."""
        defaults = {
            'id': 'lead-123',
            'first_name': 'John',
            'last_name': 'Doe',
            'company_name': 'Test Company',
            'title': 'CEO'
        }
        defaults.update(kwargs)
        
        mock_lead = Mock(spec=Lead)
        for key, value in defaults.items():
            setattr(mock_lead, key, value)
        return mock_lead

    def test_generate_email_copy_success_without_rate_limiter(self):
        """Test successful email copy generation without rate limiter."""
        with patch('app.background_services.openai_service.OpenAI') as mock_openai_class:
            # Setup mock OpenAI client
            mock_client = Mock()
            mock_openai_class.return_value = mock_client
            
            # Setup mock response
            mock_response = Mock()
            mock_response.model_dump.return_value = {
                'id': 'chatcmpl-123',
                'choices': [
                    {
                        'message': {
                            'content': 'Hi John, I hope this email finds you well...',
                            'role': 'assistant'
                        },
                        'finish_reason': 'stop'
                    }
                ],
                'usage': {'total_tokens': 150}
            }
            mock_client.chat.completions.create.return_value = mock_response
            
            # Test
            service = OpenAIService()
            lead = self.create_mock_lead()
            enrichment_data = {
                'choices': [
                    {'message': {'content': 'Company specializes in tech solutions.'}}
                ]
            }
            result = service.generate_email_copy(lead, enrichment_data)
            
            # Verify
            assert 'id' in result
            assert result['id'] == 'chatcmpl-123'
            assert 'choices' in result
            mock_client.chat.completions.create.assert_called_once()
            
            # Verify the call was made with correct parameters
            call_args = mock_client.chat.completions.create.call_args
            assert call_args[1]['model'] == 'gpt-4'
            assert call_args[1]['temperature'] == 0.7
            assert call_args[1]['max_tokens'] == 500
            assert len(call_args[1]['messages']) == 2

    def test_generate_email_copy_success_with_rate_limiter(self):
        """Test successful email copy generation with rate limiter."""
        with patch('app.background_services.openai_service.OpenAI') as mock_openai_class:
            # Setup mock OpenAI client
            mock_client = Mock()
            mock_openai_class.return_value = mock_client
            
            # Setup mock response
            mock_response = Mock()
            mock_response.model_dump.return_value = {
                'id': 'chatcmpl-123',
                'choices': [{'message': {'content': 'Generated email...'}}]
            }
            mock_client.chat.completions.create.return_value = mock_response
            
            # Setup mock rate limiter
            mock_redis = Mock()
            mock_redis.get.return_value = None
            mock_redis.pipeline.return_value = mock_redis
            mock_redis.incr.return_value = 1
            mock_redis.expire.return_value = True
            mock_redis.execute.return_value = [1, True]
            
            rate_limiter = ApiIntegrationRateLimiter(
                mock_redis, 'OpenAI', 
                settings.OPENAI_RATE_LIMIT_REQUESTS, 
                settings.OPENAI_RATE_LIMIT_PERIOD
            )
            
            # Test
            service = OpenAIService(rate_limiter=rate_limiter)
            lead = self.create_mock_lead()
            enrichment_data = {'choices': [{'message': {'content': 'Test enrichment'}}]}
            result = service.generate_email_copy(lead, enrichment_data)
            
            # Verify
            assert 'id' in result
            assert result['id'] == 'chatcmpl-123'
            mock_client.chat.completions.create.assert_called_once()

    def test_generate_email_copy_rate_limit_exceeded(self):
        """Test email copy generation when rate limit is exceeded."""
        with patch('app.background_services.openai_service.OpenAI'):
            # Setup mock rate limiter that denies requests
            mock_redis = Mock()
            mock_redis.get.return_value = '60'  # At limit
            mock_redis.pipeline.return_value = mock_redis
            mock_redis.incr.return_value = 61  # Exceeds limit
            mock_redis.execute.return_value = [61, True]
            
            rate_limiter = ApiIntegrationRateLimiter(
                mock_redis, 'OpenAI', 
                settings.OPENAI_RATE_LIMIT_REQUESTS, 
                settings.OPENAI_RATE_LIMIT_PERIOD
            )
            
            # Test
            service = OpenAIService(rate_limiter=rate_limiter)
            lead = self.create_mock_lead()
            enrichment_data = {'choices': [{'message': {'content': 'Test'}}]}
            result = service.generate_email_copy(lead, enrichment_data)
            
            # Verify rate limit response
            assert result['status'] == 'rate_limited'
            assert 'Rate limit exceeded' in result['error']
            assert 'remaining_requests' in result
            assert result['retry_after_seconds'] == settings.OPENAI_RATE_LIMIT_PERIOD

    def test_generate_email_copy_missing_required_fields(self):
        """Test email copy generation with missing required fields."""
        with patch('app.background_services.openai_service.OpenAI'):
            service = OpenAIService()
            
            # Test missing first_name
            lead = self.create_mock_lead(first_name='')
            enrichment_data = {}
            result = service.generate_email_copy(lead, enrichment_data)
            
            assert result['status'] == 'error'
            assert 'Missing required prompt variables' in result['error']
            assert 'first_name' in result['error']

    def test_generate_email_copy_openai_api_error(self):
        """Test email copy generation with OpenAI API error."""
        with patch('app.background_services.openai_service.OpenAI') as mock_openai_class:
            # Setup mock client to raise exception
            mock_client = Mock()
            mock_openai_class.return_value = mock_client
            mock_client.chat.completions.create.side_effect = Exception("OpenAI API Error")
            
            # Test
            service = OpenAIService()
            lead = self.create_mock_lead()
            enrichment_data = {'choices': [{'message': {'content': 'Test'}}]}
            result = service.generate_email_copy(lead, enrichment_data)
            
            # Verify error response
            assert result['status'] == 'error'
            assert 'OpenAI API Error' in result['error']

    def test_generate_email_copy_rate_limiter_failure_graceful_degradation(self):
        """Test that rate limiter failures don't prevent email copy generation."""
        with patch('app.background_services.openai_service.OpenAI') as mock_openai_class:
            # Setup mock rate limiter that fails
            mock_redis = Mock()
            mock_redis.get.side_effect = Exception("Redis connection failed")
            
            rate_limiter = ApiIntegrationRateLimiter(
                mock_redis, 'OpenAI', 
                settings.OPENAI_RATE_LIMIT_REQUESTS, 
                settings.OPENAI_RATE_LIMIT_PERIOD
            )
            
            # Setup successful OpenAI response
            mock_client = Mock()
            mock_openai_class.return_value = mock_client
            mock_response = Mock()
            mock_response.model_dump.return_value = {
                'id': 'chatcmpl-123',
                'choices': [{'message': {'content': 'Generated email'}}]
            }
            mock_client.chat.completions.create.return_value = mock_response
            
            # Test
            service = OpenAIService(rate_limiter=rate_limiter)
            lead = self.create_mock_lead()
            enrichment_data = {'choices': [{'message': {'content': 'Test'}}]}
            result = service.generate_email_copy(lead, enrichment_data)
            
            # Verify that API call still succeeded despite rate limiter failure
            assert 'id' in result
            assert result['id'] == 'chatcmpl-123'
            mock_client.chat.completions.create.assert_called_once()

    def test_generate_email_copy_with_empty_enrichment(self):
        """Test email copy generation with empty enrichment data."""
        with patch('app.background_services.openai_service.OpenAI') as mock_openai_class:
            # Setup mock OpenAI client
            mock_client = Mock()
            mock_openai_class.return_value = mock_client
            
            # Setup mock response
            mock_response = Mock()
            mock_response.model_dump.return_value = {
                'id': 'chatcmpl-123',
                'choices': [{'message': {'content': 'Generated email without enrichment'}}]
            }
            mock_client.chat.completions.create.return_value = mock_response
            
            # Test with empty enrichment data
            service = OpenAIService()
            lead = self.create_mock_lead()
            enrichment_data = {}  # Empty enrichment
            result = service.generate_email_copy(lead, enrichment_data)
            
            # Verify
            assert 'id' in result
            assert result['id'] == 'chatcmpl-123'
            mock_client.chat.completions.create.assert_called_once()

    def test_generate_email_copy_with_mock_redis_integration(self):
        """Integration test with mock Redis for rate limiting behavior."""
        with patch('app.background_services.openai_service.OpenAI') as mock_openai_class:
            # Setup mock Redis that allows first request, denies second
            mock_redis = Mock()
            call_count = 0
            
            def mock_execute():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return [1, True]  # First call succeeds
                else:
                    return [2, True]  # Second call exceeds limit of 1
                    
            mock_redis.get.return_value = None
            mock_redis.pipeline.return_value = mock_redis
            mock_redis.execute.side_effect = mock_execute
            
            # Create rate limiter with limit of 1 request for this test
            rate_limiter = ApiIntegrationRateLimiter(
                mock_redis, 'OpenAI', 
                1,  # Use limit of 1 for this specific test to simulate rate limiting
                settings.OPENAI_RATE_LIMIT_PERIOD
            )
            
            # Setup successful OpenAI response - fix the mock chain
            mock_client = Mock()
            mock_openai_class.return_value = mock_client
            
            # Create a proper mock response that returns dict when model_dump() is called
            expected_response = {
                'id': 'chatcmpl-123',
                'choices': [{'message': {'content': 'Generated email'}}]
            }
            mock_response = Mock()
            mock_response.model_dump.return_value = expected_response
            mock_client.chat.completions.create.return_value = mock_response
            
            service = OpenAIService(rate_limiter=rate_limiter)
            
            # First call should succeed
            lead1 = self.create_mock_lead(id='lead-1')
            enrichment_data = {'choices': [{'message': {'content': 'Test'}}]}
            result1 = service.generate_email_copy(lead1, enrichment_data)
            
            # Verify the result is the expected dictionary
            assert result1 == expected_response
            assert result1['id'] == 'chatcmpl-123'
            
            # Second call should be rate limited
            lead2 = self.create_mock_lead(id='lead-2')
            result2 = service.generate_email_copy(lead2, enrichment_data)
            assert result2['status'] == 'rate_limited'

    def test_lead_with_company_attribute_fallback(self):
        """Test that the service handles leads with 'company' instead of 'company_name'."""
        with patch('app.background_services.openai_service.OpenAI') as mock_openai_class:
            # Setup mock OpenAI client
            mock_client = Mock()
            mock_openai_class.return_value = mock_client
            
            mock_response = Mock()
            mock_response.model_dump.return_value = {
                'id': 'chatcmpl-123',
                'choices': [{'message': {'content': 'Generated email'}}]
            }
            mock_client.chat.completions.create.return_value = mock_response
            
            # Test with lead that has 'company' instead of 'company_name'
            service = OpenAIService()
            lead = self.create_mock_lead(company_name=None)
            lead.company = 'Fallback Company'  # Use company attribute instead
            enrichment_data = {'choices': [{'message': {'content': 'Test'}}]}
            result = service.generate_email_copy(lead, enrichment_data)
            
            # Verify
            assert 'id' in result
            mock_client.chat.completions.create.assert_called_once()

# Integration tests that could be run with actual services (when available)
class TestOpenAIServiceIntegration:
    """Integration tests for OpenAIService (require external services)."""
    
    @pytest.mark.skip(reason="Requires OpenAI API key and Redis connection")
    def test_real_openai_integration(self):
        """Test with real OpenAI API connection (skipped by default)."""
        # This test would require actual OpenAI API setup
        # Uncomment and configure when running integration tests
        pass

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"]) 