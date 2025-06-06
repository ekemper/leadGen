#!/usr/bin/env python3
"""
Test script to demonstrate the new Perplexity timing logging functionality.

This script shows how the enhanced PerplexityService logs detailed timing information
for each request attempt, including rate limiter decisions and response details.

Usage:
    python scripts/test_perplexity_timing_logs.py

The script will make mock requests and show the timing logs that would be generated.
"""

import sys
import os
import time
from unittest.mock import Mock, patch

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.background_services.perplexity_service import PerplexityService
from app.models.lead import Lead
from app.core.api_integration_rate_limiter import ApiIntegrationRateLimiter


def create_test_lead():
    """Create a test lead for demonstration."""
    return Lead(
        id="demo-lead-123",
        campaign_id="demo-campaign-456",
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        company="Demo Company",
        title="Software Engineer",
        raw_data={"headline": "Senior Software Engineer"}
    )


def create_mock_rate_limiter():
    """Create a mock rate limiter for demonstration."""
    mock_limiter = Mock(spec=ApiIntegrationRateLimiter)
    mock_limiter.max_requests = 1
    mock_limiter.period_seconds = 5
    mock_limiter.acquire.return_value = True
    mock_limiter.get_remaining.return_value = 0
    mock_limiter.get_time_since_last_request.return_value = 3.2
    mock_limiter.get_last_request_time.return_value = time.time() - 3.2
    return mock_limiter


def demo_successful_request():
    """Demonstrate logging for a successful request."""
    print("\n" + "="*60)
    print("DEMO 1: Successful Request with Rate Limiter")
    print("="*60)
    
    with patch.dict('os.environ', {'PERPLEXITY_TOKEN': 'demo_token'}):
        # Create service with rate limiter
        rate_limiter = create_mock_rate_limiter()
        service = PerplexityService(rate_limiter=rate_limiter)
        
        # Mock successful API response
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                'choices': [{'message': {'content': 'Demo enrichment data'}}]
            }
            mock_response.raise_for_status.return_value = None
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            # Make request
            lead = create_test_lead()
            result = service.enrich_lead(lead)
            
            print(f"Result: {result}")
            print("\nExpected log entries:")
            print("1. 'perplexity timing test log - Request Attempt' with timing details")
            print("2. 'perplexity timing test log - Request Response' with success status")


def demo_rate_limited_request():
    """Demonstrate logging for a rate-limited request."""
    print("\n" + "="*60)
    print("DEMO 2: Rate Limited Request")
    print("="*60)
    
    with patch.dict('os.environ', {'PERPLEXITY_TOKEN': 'demo_token'}):
        # Create service with rate limiter that denies requests
        rate_limiter = create_mock_rate_limiter()
        rate_limiter.acquire.return_value = False
        rate_limiter.get_remaining.return_value = 0
        rate_limiter.get_time_since_last_request.return_value = 1.5  # Too soon
        
        service = PerplexityService(rate_limiter=rate_limiter)
        
        # Make request
        lead = create_test_lead()
        result = service.enrich_lead(lead)
        
        print(f"Result: {result}")
        print("\nExpected log entries:")
        print("1. 'perplexity timing test log - Request Attempt' with rate_limiter_decision=denied")
        print("2. 'perplexity timing test log - Request Response' with response_status=rate_limited")


def demo_no_rate_limiter():
    """Demonstrate logging without rate limiter."""
    print("\n" + "="*60)
    print("DEMO 3: Request Without Rate Limiter")
    print("="*60)
    
    with patch.dict('os.environ', {'PERPLEXITY_TOKEN': 'demo_token'}):
        # Create service without rate limiter
        service = PerplexityService()
        
        # Mock successful API response
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                'choices': [{'message': {'content': 'Demo enrichment data'}}]
            }
            mock_response.raise_for_status.return_value = None
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            # Make request
            lead = create_test_lead()
            result = service.enrich_lead(lead)
            
            print(f"Result: {result}")
            print("\nExpected log entries:")
            print("1. 'perplexity timing test log - Request Attempt' with rate_limiter_decision=no_limiter")
            print("2. 'perplexity timing test log - Request Response' with success status")


def demo_api_error():
    """Demonstrate logging for API errors."""
    print("\n" + "="*60)
    print("DEMO 4: API Error with Retries")
    print("="*60)
    
    with patch.dict('os.environ', {'PERPLEXITY_TOKEN': 'demo_token'}):
        # Create service with rate limiter
        rate_limiter = create_mock_rate_limiter()
        service = PerplexityService(rate_limiter=rate_limiter)
        
        # Mock API error
        with patch('requests.post') as mock_post:
            import requests
            mock_post.side_effect = requests.RequestException("Connection timeout")
            
            # Make request
            lead = create_test_lead()
            result = service.enrich_lead(lead)
            
            print(f"Result: {result}")
            print("\nExpected log entries:")
            print("1. Multiple 'perplexity timing test log - Request Attempt' entries (for retries)")
            print("2. Multiple 'perplexity timing test log - Request Response' entries with error status")


def main():
    """Run all demonstrations."""
    print("Perplexity Timing Logging Demonstration")
    print("This script shows the new logging functionality added to PerplexityService")
    print("In a real environment, these logs would appear in your application logs")
    print("and can be easily filtered using: grep 'perplexity timing test log'")
    
    demo_successful_request()
    demo_rate_limited_request()
    demo_no_rate_limiter()
    demo_api_error()
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("The enhanced PerplexityService now logs:")
    print("• Each request attempt with correlation ID and timing details")
    print("• Rate limiter decisions (allowed/denied/no_limiter/error_fallback)")
    print("• Time since last request (for debugging rate limiting issues)")
    print("• Response status and timing for each attempt")
    print("• Correlation IDs for tracing requests across logs")
    print("\nTo view these logs in production:")
    print("  grep 'perplexity timing test log' /path/to/logs")
    print("\nThis will help debug why conservative rate limiting (1 req/5s)")
    print("is still hitting Perplexity's rate limits.")


if __name__ == "__main__":
    main() 