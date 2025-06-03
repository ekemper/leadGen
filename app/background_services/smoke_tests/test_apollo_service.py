"""
Tests for ApolloService with Rate Limiting Integration

This test suite validates the ApolloService functionality including:
- Backward compatibility for existing usage patterns
- Rate limiting integration and behavior for bulk operations
- Error handling and graceful degradation
- Mock Apify client integration
- Database interaction testing
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from app.background_services.apollo_service import ApolloService
from app.core.api_integration_rate_limiter import ApiIntegrationRateLimiter
from app.models.lead import Lead

class TestApolloService:
    """Test suite for ApolloService."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Mock the environment variables
        self.api_token_patcher = patch.dict('os.environ', {
            'APIFY_API_TOKEN': 'test-api-token',
            'USE_APIFY_CLIENT_MOCK': 'false'
        })
        self.api_token_patcher.start()
        
    def teardown_method(self):
        """Cleanup after each test method."""
        self.api_token_patcher.stop()

    def test_backward_compatibility_initialization(self):
        """Test that ApolloService can be initialized without rate limiter (backward compatibility)."""
        with patch('app.background_services.apollo_service.ApifyClient'):
            service = ApolloService()
            
            assert service.api_token == 'test-api-token'
            assert service.actor_id == "code_crafter/apollo-io-scraper"
            assert service.rate_limiter is None
        
    def test_rate_limiter_initialization(self):
        """Test that ApolloService can be initialized with rate limiter."""
        with patch('app.background_services.apollo_service.ApifyClient'):
            mock_redis = Mock()
            rate_limiter = ApiIntegrationRateLimiter(mock_redis, 'Apollo', 30, 60)
            
            service = ApolloService(rate_limiter=rate_limiter)
            
            assert service.rate_limiter is rate_limiter
            assert service.api_token == 'test-api-token'
        
    def test_missing_api_token_raises_error(self):
        """Test that missing API token raises ValueError."""
        # Stop the current patcher
        self.api_token_patcher.stop()
        
        # Mock load_dotenv to do nothing and os.getenv to return None for APIFY_API_TOKEN
        with patch('app.background_services.apollo_service.load_dotenv'):
            with patch('app.background_services.apollo_service.os.getenv') as mock_getenv:
                mock_getenv.return_value = None  # Simulate missing API token
                
                with pytest.raises(ValueError, match="APIFY_API_TOKEN environment variable is not set"):
                    ApolloService()
        
        # Restart the patcher for subsequent tests
        self.api_token_patcher.start()

    def test_mock_client_usage(self):
        """Test that mock client is used when environment variable is set."""
        with patch.dict('os.environ', {'USE_APIFY_CLIENT_MOCK': 'true'}):
            with patch('app.background_services.apollo_service.MockApifyClient') as mock_apify:
                service = ApolloService()
                mock_apify.assert_called_once_with('test-api-token')

    def test_fetch_leads_missing_required_params(self):
        """Test that fetch_leads raises error for missing required parameters."""
        with patch('app.background_services.apollo_service.ApifyClient'):
            service = ApolloService()
            
            # Test missing fileName
            incomplete_params = {'totalRecords': 100, 'url': 'http://example.com'}
            
            with pytest.raises(ValueError, match="Missing required parameter: fileName"):
                service.fetch_leads(incomplete_params, 'test-campaign-id')

    @patch('app.background_services.apollo_service.ApifyClient')
    def test_fetch_leads_success_without_rate_limiter(self, mock_apify_client):
        """Test successful lead fetching without rate limiter."""
        # Setup mock Apify client
        mock_client = Mock()
        mock_apify_client.return_value = mock_client
        
        # Setup mock actor and dataset responses
        mock_actor = Mock()
        mock_client.actor.return_value = mock_actor
        mock_actor.call.return_value = {'defaultDatasetId': 'test-dataset-id'}
        
        mock_dataset = Mock()
        mock_client.dataset.return_value = mock_dataset
        mock_dataset.iterate_items.return_value = [
            {
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john@example.com',
                'organization': {'name': 'Test Company'},
                'title': 'CEO'
            },
            {
                'first_name': 'Jane',
                'last_name': 'Smith', 
                'email': 'jane@example.com',
                'organization_name': 'Another Company',
                'title': 'CTO'
            }
        ]
        
        # Mock database session
        mock_db = Mock()
        mock_db.commit.return_value = None
        
        # Test
        service = ApolloService()
        params = {'fileName': 'test.csv', 'totalRecords': 100, 'url': 'http://example.com'}
        result = service.fetch_leads(params, 'test-campaign-id', mock_db)
        
        # Verify
        assert result['count'] == 2
        assert result['errors'] == []
        mock_actor.call.assert_called_once_with(run_input=params)
        mock_dataset.iterate_items.assert_called_once()
        
    @patch('app.background_services.apollo_service.ApifyClient')
    def test_fetch_leads_success_with_rate_limiter(self, mock_apify_client):
        """Test successful lead fetching with rate limiter."""
        # Setup mock Apify client
        mock_client = Mock()
        mock_apify_client.return_value = mock_client
        
        mock_actor = Mock()
        mock_client.actor.return_value = mock_actor
        mock_actor.call.return_value = {'defaultDatasetId': 'test-dataset-id'}
        
        mock_dataset = Mock()
        mock_client.dataset.return_value = mock_dataset
        mock_dataset.iterate_items.return_value = [
            {'first_name': 'John', 'email': 'john@example.com'}
        ]
        
        # Setup mock rate limiter that allows requests
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_redis.pipeline.return_value = mock_redis
        mock_redis.execute.return_value = [1, True]
        
        rate_limiter = ApiIntegrationRateLimiter(mock_redis, 'Apollo', 30, 60)
        
        # Mock database session
        mock_db = Mock()
        
        # Test
        service = ApolloService(rate_limiter=rate_limiter)
        params = {'fileName': 'test.csv', 'totalRecords': 100, 'url': 'http://example.com'}
        result = service.fetch_leads(params, 'test-campaign-id', mock_db)
        
        # Verify
        assert result['count'] == 1
        assert 'errors' in result
        mock_actor.call.assert_called_once()

    def test_fetch_leads_rate_limit_exceeded(self):
        """Test lead fetching when rate limit is exceeded."""
        with patch('app.background_services.apollo_service.ApifyClient'):
            # Setup mock rate limiter that denies requests
            mock_redis = Mock()
            mock_redis.get.return_value = '30'  # At limit
            mock_redis.pipeline.return_value = mock_redis
            mock_redis.execute.return_value = [31, True]  # Exceeds limit
            
            rate_limiter = ApiIntegrationRateLimiter(mock_redis, 'Apollo', 30, 60)
            
            # Test
            service = ApolloService(rate_limiter=rate_limiter)
            params = {'fileName': 'test.csv', 'totalRecords': 100, 'url': 'http://example.com'}
            result = service.fetch_leads(params, 'test-campaign-id')
            
            # Verify rate limit response
            assert result['count'] == 0
            assert result['rate_limited'] is True
            assert 'Rate limit exceeded' in result['errors'][0]
            assert 'remaining_requests' in result
            assert result['retry_after_seconds'] == 60

    @patch('app.background_services.apollo_service.ApifyClient')
    def test_fetch_leads_apify_error(self, mock_apify_client):
        """Test lead fetching with Apify API error."""
        # Setup mock client to raise exception
        mock_client = Mock()
        mock_apify_client.return_value = mock_client
        mock_actor = Mock()
        mock_client.actor.return_value = mock_actor
        mock_actor.call.side_effect = Exception("Apify API Error")
        
        # Test
        service = ApolloService()
        params = {'fileName': 'test.csv', 'totalRecords': 100, 'url': 'http://example.com'}
        
        # The service wraps the original exception message
        with pytest.raises(Exception, match="Apify API Error"):
            service.fetch_leads(params, 'test-campaign-id')

    @patch('app.background_services.apollo_service.ApifyClient')
    def test_fetch_leads_no_dataset_id(self, mock_apify_client):
        """Test lead fetching when no dataset ID is returned."""
        # Setup mock client
        mock_client = Mock()
        mock_apify_client.return_value = mock_client
        mock_actor = Mock()
        mock_client.actor.return_value = mock_actor
        mock_actor.call.return_value = {}  # No dataset ID
        
        # Test
        service = ApolloService()
        params = {'fileName': 'test.csv', 'totalRecords': 100, 'url': 'http://example.com'}
        
        # The service throws the original exception without wrapping
        with pytest.raises(Exception, match="No dataset ID returned from Apify actor run."):
            service.fetch_leads(params, 'test-campaign-id')

    def test_fetch_leads_rate_limiter_failure_graceful_degradation(self):
        """Test that rate limiter failures don't prevent lead fetching."""
        with patch('app.background_services.apollo_service.ApifyClient') as mock_apify_client:
            # Setup mock rate limiter that fails
            mock_redis = Mock()
            mock_redis.get.side_effect = Exception("Redis connection failed")
            
            rate_limiter = ApiIntegrationRateLimiter(mock_redis, 'Apollo', 30, 60)
            
            # Setup successful Apify response
            mock_client = Mock()
            mock_apify_client.return_value = mock_client
            mock_actor = Mock()
            mock_client.actor.return_value = mock_actor
            mock_actor.call.return_value = {'defaultDatasetId': 'test-dataset-id'}
            mock_dataset = Mock()
            mock_client.dataset.return_value = mock_dataset
            mock_dataset.iterate_items.return_value = [{'email': 'test@example.com'}]
            
            # Mock database
            mock_db = Mock()
            
            # Test
            service = ApolloService(rate_limiter=rate_limiter)
            params = {'fileName': 'test.csv', 'totalRecords': 100, 'url': 'http://example.com'}
            result = service.fetch_leads(params, 'test-campaign-id', mock_db)
            
            # Verify that API call still succeeded despite rate limiter failure
            assert result['count'] == 1
            mock_actor.call.assert_called_once()

    @patch('app.background_services.apollo_service.ApifyClient')
    def test_save_leads_to_db_success(self, mock_apify_client):
        """Test successful lead saving to database."""
        # Setup service
        service = ApolloService()
        
        # Mock database session
        mock_db = Mock()
        mock_db.commit.return_value = None
        
        # Mock query to return no existing emails
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        
        # Test data
        leads_data = [
            {
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john@example.com',
                'phone': '+1234567890',
                'organization': {'name': 'Test Company'},
                'title': 'CEO',
                'linkedin_url': 'https://linkedin.com/in/johndoe'
            },
            {
                'first_name': 'Jane',
                'email': 'jane@example.com',
                'organization_name': 'Another Company'
            }
        ]
        
        # Test
        result = service._save_leads_to_db(leads_data, 'test-campaign-id', mock_db)
        
        # Verify
        assert result['created'] == 2
        assert result['skipped'] == 0
        assert result['errors'] == 0
        assert mock_db.add.call_count == 2
        mock_db.commit.assert_called_once()

    @patch('app.background_services.apollo_service.ApifyClient')
    def test_save_leads_to_db_no_session(self, mock_apify_client):
        """Test lead saving with no database session."""
        service = ApolloService()
        
        # Test with None database session
        result = service._save_leads_to_db([{'email': 'test@example.com'}], 'test-campaign-id', None)
        
        # Verify
        assert result['created'] == 0
        assert result['skipped'] == 0
        assert result['errors'] == 0

    @patch('app.background_services.apollo_service.ApifyClient')
    def test_save_leads_to_db_commit_error(self, mock_apify_client):
        """Test lead saving with database commit error."""
        service = ApolloService()
        
        # Mock database session that fails on commit
        mock_db = Mock()
        mock_db.commit.side_effect = Exception("Database error")
        
        leads_data = [{'email': 'test@example.com'}]
        
        # Test
        with pytest.raises(Exception, match="Database error"):
            service._save_leads_to_db(leads_data, 'test-campaign-id', mock_db)
        
        # Verify rollback was called
        mock_db.rollback.assert_called_once()

    @patch('app.background_services.apollo_service.ApifyClient')
    def test_save_leads_to_db_duplicate_prevention(self, mock_apify_client):
        """Test that _save_leads_to_db prevents duplicate emails."""
        service = ApolloService()
        
        # Mock database session with query results
        mock_db = Mock()
        mock_db.commit.return_value = None
        
        # Mock existing email query - simulate that one email already exists
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [('existing@example.com',)]
        
        # Test data with some duplicates
        leads_data = [
            {
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john@example.com',
                'organization': {'name': 'Test Company'},
                'title': 'CEO'
            },
            {
                'first_name': 'Jane',
                'last_name': 'Smith',
                'email': 'EXISTING@EXAMPLE.COM',  # Case different but same email
                'organization_name': 'Another Company',
                'title': 'CTO'
            },
            {
                'first_name': 'Bob',
                'last_name': 'Wilson',
                'email': 'bob@example.com',
                'title': 'Developer'
            },
            {
                'first_name': 'Alice',
                'last_name': 'Brown',
                'email': '  john@example.com  ',  # Duplicate within batch (with spaces)
                'title': 'Designer'
            },
            {
                'first_name': 'Charlie',
                'last_name': 'Davis',
                'email': '',  # Empty email
                'title': 'Manager'
            },
            {
                'first_name': 'David',
                'last_name': 'Miller',
                # No email field
                'title': 'Analyst'
            }
        ]
        
        # Test
        result = service._save_leads_to_db(leads_data, 'test-campaign-id', mock_db)
        
        # Verify results
        assert result['created'] == 2  # john@example.com and bob@example.com
        assert result['skipped'] == 4  # existing email + duplicate within batch + empty email + no email
        assert result['errors'] == 0
        
        # Verify that only 2 leads were added to the session
        assert mock_db.add.call_count == 2
        mock_db.commit.assert_called_once()
        
        # Check the query was called correctly
        mock_db.query.assert_called_once()

    @patch('app.background_services.apollo_service.ApifyClient')
    def test_save_leads_to_db_database_error_during_duplicate_check(self, mock_apify_client):
        """Test that _save_leads_to_db handles database errors during duplicate checking gracefully."""
        service = ApolloService()
        
        # Mock database session that fails on query
        mock_db = Mock()
        mock_db.commit.return_value = None
        mock_db.query.side_effect = Exception("Database connection error")
        
        leads_data = [
            {
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john@example.com',
                'title': 'CEO'
            }
        ]
        
        # Test - should continue processing even if duplicate check fails
        result = service._save_leads_to_db(leads_data, 'test-campaign-id', mock_db)
        
        # Verify that lead was still created (duplicate check failed gracefully)
        assert result['created'] == 1
        assert result['skipped'] == 0
        assert result['errors'] == 0
        
        assert mock_db.add.call_count == 1
        mock_db.commit.assert_called_once()

    @patch('app.background_services.apollo_service.ApifyClient')
    def test_save_leads_to_db_individual_lead_error(self, mock_apify_client):
        """Test that _save_leads_to_db handles individual lead creation errors."""
        service = ApolloService()
        
        # Mock database session
        mock_db = Mock()
        mock_db.commit.return_value = None
        
        # Mock query to return no existing emails
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        
        # Mock Lead creation to fail for specific cases
        with patch('app.background_services.apollo_service.Lead') as mock_lead_class:
            def side_effect(*args, **kwargs):
                if kwargs.get('email') == 'error@example.com':
                    raise Exception("Database constraint violation")
                return Mock()
            
            mock_lead_class.side_effect = side_effect
            
            leads_data = [
                {
                    'first_name': 'John',
                    'email': 'john@example.com',
                    'title': 'CEO'
                },
                {
                    'first_name': 'Error',
                    'email': 'error@example.com',  # This will trigger an error
                    'title': 'Manager'
                },
                {
                    'first_name': 'Jane',
                    'email': 'jane@example.com',
                    'title': 'Developer'
                }
            ]
            
            # Test
            result = service._save_leads_to_db(leads_data, 'test-campaign-id', mock_db)
            
            # Verify results
            assert result['created'] == 2  # john and jane
            assert result['skipped'] == 0
            assert result['errors'] == 1  # error lead
            
            assert mock_db.add.call_count == 2  # Only successful leads added
            mock_db.commit.assert_called_once()

    @patch('app.background_services.apollo_service.ApifyClient')
    def test_fetch_leads_with_duplicate_prevention_reporting(self, mock_apify_client):
        """Test that fetch_leads reports duplicate prevention statistics."""
        # Setup mock Apify client
        mock_client = Mock()
        mock_apify_client.return_value = mock_client
        
        mock_actor = Mock()
        mock_client.actor.return_value = mock_actor
        mock_actor.call.return_value = {'defaultDatasetId': 'test-dataset-id'}
        
        mock_dataset = Mock()
        mock_client.dataset.return_value = mock_dataset
        mock_dataset.iterate_items.return_value = [
            {'first_name': 'John', 'email': 'john@example.com'},
            {'first_name': 'Jane', 'email': 'existing@example.com'},  # Will be duplicate
            {'first_name': 'Bob', 'email': 'bob@example.com'}
        ]
        
        # Mock database session with existing email
        mock_db = Mock()
        mock_db.commit.return_value = None
        
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [('existing@example.com',)]
        
        # Test
        service = ApolloService()
        params = {'fileName': 'test.csv', 'totalRecords': 100, 'url': 'http://example.com'}
        result = service.fetch_leads(params, 'test-campaign-id', mock_db)
        
        # Verify detailed statistics in response
        assert result['count'] == 2  # john and bob created
        assert result['created'] == 2
        assert result['skipped'] == 1  # existing email skipped
        assert result['total_processed'] == 3
        assert 'Skipped 1 duplicate/invalid emails' in result['errors']
        
        mock_actor.call.assert_called_once_with(run_input=params)
        mock_dataset.iterate_items.assert_called_once()

    @patch('app.background_services.apollo_service.ApifyClient')
    def test_duplicate_prevention_integration(self, mock_apify_client):
        """Integration test demonstrating complete duplicate prevention workflow."""
        # Setup mock Apify client
        mock_client = Mock()
        mock_apify_client.return_value = mock_client
        
        mock_actor = Mock()
        mock_client.actor.return_value = mock_actor
        mock_actor.call.return_value = {'defaultDatasetId': 'test-dataset-id'}
        
        mock_dataset = Mock()
        mock_client.dataset.return_value = mock_dataset
        
        # First batch of leads
        mock_dataset.iterate_items.return_value = [
            {'first_name': 'John', 'email': 'john@example.com', 'title': 'CEO'},
            {'first_name': 'Jane', 'email': 'jane@example.com', 'title': 'CTO'},
        ]
        
        # Mock database session
        mock_db = Mock()
        mock_db.commit.return_value = None
        
        # Mock initial query (no existing emails)
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        
        # Test service
        service = ApolloService()
        params = {'fileName': 'test.csv', 'totalRecords': 100, 'url': 'http://example.com'}
        
        # First fetch - should create both leads
        result1 = service.fetch_leads(params, 'test-campaign-1', mock_db)
        
        assert result1['created'] == 2
        assert result1['skipped'] == 0
        assert result1['total_processed'] == 2
        assert len(result1['errors']) == 0
        
        # Now simulate second batch with some duplicates
        mock_dataset.iterate_items.return_value = [
            {'first_name': 'John', 'email': 'john@example.com', 'title': 'CEO'},  # Duplicate
            {'first_name': 'Bob', 'email': 'bob@example.com', 'title': 'Developer'},  # New
            {'first_name': 'Jane', 'email': 'JANE@EXAMPLE.COM', 'title': 'CTO'},  # Duplicate (case different)
        ]
        
        # Mock query to return existing emails from first batch
        mock_query.all.return_value = [('john@example.com',), ('jane@example.com',)]
        
        # Second fetch - should only create Bob, skip duplicates
        result2 = service.fetch_leads(params, 'test-campaign-2', mock_db)
        
        assert result2['created'] == 1  # Only Bob created
        assert result2['skipped'] == 2  # John and Jane skipped
        assert result2['total_processed'] == 3
        assert 'Skipped 2 duplicate/invalid emails' in result2['errors']
        
        # Verify total database interactions
        # First batch: 2 adds, Second batch: 1 add = 3 total
        assert mock_db.add.call_count == 3
        assert mock_db.commit.call_count == 2

# Integration tests that could be run with actual services (when available)
class TestApolloServiceIntegration:
    """Integration tests for ApolloService (require external services)."""
    
    @pytest.mark.skip(reason="Requires Apify connection and API token")
    def test_real_apify_integration(self):
        """Test with real Apify connection (skipped by default)."""
        # This test would require actual Apify setup
        # Uncomment and configure when running integration tests
        pass

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"]) 