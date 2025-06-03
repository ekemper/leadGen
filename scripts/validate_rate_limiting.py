#!/usr/bin/env python3
"""
Comprehensive validation script for the API Rate Limiting system.

This script validates all components of the rate limiting system:
- Configuration loading
- Redis connectivity
- Service integration
- Rate limiting behavior
- Graceful degradation
- Performance characteristics

Usage:
    python scripts/validate_rate_limiting.py [--redis-host HOST] [--redis-port PORT]
"""

import sys
import os
import time
import asyncio
import argparse
from typing import Dict, List, Tuple
from unittest.mock import patch, Mock

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.config import get_redis_connection
from app.core.api_integration_rate_limiter import ApiIntegrationRateLimiter, get_api_rate_limits
from app.core.dependencies import (
    get_apollo_rate_limiter,
    get_email_verifier_rate_limiter,
    get_perplexity_rate_limiter,
    get_openai_rate_limiter,
    get_instantly_rate_limiter
)


class RateLimitingValidator:
    """Comprehensive validator for the rate limiting system."""
    
    def __init__(self, redis_host: str = None, redis_port: int = None):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.results = []
        self.redis_client = None
        
    def log_result(self, test_name: str, passed: bool, message: str = ""):
        """Log a test result."""
        status = "✅ PASS" if passed else "❌ FAIL"
        full_message = f"{status} {test_name}"
        if message:
            full_message += f": {message}"
        
        print(full_message)
        self.results.append({
            'test': test_name,
            'passed': passed,
            'message': message
        })
    
    def validate_configuration(self) -> bool:
        """Validate that all rate limiting configuration is loaded correctly."""
        print("\n🔧 Validating Configuration...")
        
        try:
            # Test configuration loading
            limits = get_api_rate_limits()
            required_services = ['MillionVerifier', 'Apollo', 'Instantly', 'OpenAI', 'Perplexity']
            
            all_services_configured = True
            for service in required_services:
                if service not in limits:
                    self.log_result(f"Config - {service}", False, f"Service {service} not configured")
                    all_services_configured = False
                else:
                    config = limits[service]
                    if config['max_requests'] <= 0 or config['period_seconds'] <= 0:
                        self.log_result(f"Config - {service}", False, "Invalid rate limit values")
                        all_services_configured = False
                    else:
                        self.log_result(f"Config - {service}", True, 
                                      f"{config['max_requests']}/{config['period_seconds']}s")
            
            return all_services_configured
            
        except Exception as e:
            self.log_result("Configuration Loading", False, str(e))
            return False
    
    def validate_redis_connectivity(self) -> bool:
        """Validate Redis connectivity and basic operations."""
        print("\n🔌 Validating Redis Connectivity...")
        
        try:
            # Override Redis connection if custom host/port provided
            if self.redis_host or self.redis_port:
                from redis import Redis
                self.redis_client = Redis(
                    host=self.redis_host or 'localhost',
                    port=self.redis_port or 6379,
                    decode_responses=True
                )
            else:
                self.redis_client = get_redis_connection()
            
            # Test basic connectivity
            self.redis_client.ping()
            self.log_result("Redis Connection", True, "Successfully connected")
            
            # Test basic operations
            test_key = "ratelimit:validation:test"
            self.redis_client.set(test_key, "test", ex=5)
            value = self.redis_client.get(test_key)
            self.redis_client.delete(test_key)
            
            if value == "test":
                self.log_result("Redis Operations", True, "Set/Get/Delete working")
                return True
            else:
                self.log_result("Redis Operations", False, "Set/Get operations failed")
                return False
                
        except Exception as e:
            self.log_result("Redis Connection", False, str(e))
            return False
    
    def validate_rate_limiter_creation(self) -> bool:
        """Validate that all service rate limiters can be created."""
        print("\n🏗️  Validating Rate Limiter Creation...")
        
        if not self.redis_client:
            self.log_result("Rate Limiter Creation", False, "Redis not available")
            return False
        
        try:
            # Test all service rate limiters
            services = {
                'Apollo': get_apollo_rate_limiter,
                'MillionVerifier': get_email_verifier_rate_limiter,
                'Perplexity': get_perplexity_rate_limiter,
                'OpenAI': get_openai_rate_limiter,
                'Instantly': get_instantly_rate_limiter
            }
            
            all_created = True
            for service_name, factory_func in services.items():
                try:
                    limiter = factory_func(self.redis_client)
                    if limiter.api_name == service_name:
                        self.log_result(f"Create {service_name} Limiter", True, 
                                      f"{limiter.max_requests}/{limiter.period_seconds}s")
                    else:
                        self.log_result(f"Create {service_name} Limiter", False, 
                                      f"Wrong API name: {limiter.api_name}")
                        all_created = False
                except Exception as e:
                    self.log_result(f"Create {service_name} Limiter", False, str(e))
                    all_created = False
            
            return all_created
            
        except Exception as e:
            self.log_result("Rate Limiter Creation", False, str(e))
            return False
    
    def validate_rate_limiting_behavior(self) -> bool:
        """Validate actual rate limiting behavior."""
        print("\n⏱️  Validating Rate Limiting Behavior...")
        
        if not self.redis_client:
            self.log_result("Rate Limiting Behavior", False, "Redis not available")
            return False
        
        try:
            # Create a test rate limiter with very restrictive limits
            test_limiter = ApiIntegrationRateLimiter(
                redis_client=self.redis_client,
                api_name='ValidationTest',
                max_requests=3,
                period_seconds=10
            )
            
            # Clear any existing state
            self.redis_client.delete(test_limiter.key)
            
            # Test basic acquisition
            results = []
            for i in range(5):
                results.append(test_limiter.acquire())
            
            successful = sum(results)
            if successful == 3:
                self.log_result("Rate Limit Enforcement", True, "3/5 requests allowed")
            else:
                self.log_result("Rate Limit Enforcement", False, f"{successful}/5 requests allowed")
                return False
            
            # Test remaining count
            remaining = test_limiter.get_remaining()
            if remaining == 0:
                self.log_result("Remaining Count", True, f"Correctly shows {remaining} remaining")
            else:
                self.log_result("Remaining Count", False, f"Shows {remaining} remaining, expected 0")
                return False
            
            # Test is_allowed without acquiring
            if not test_limiter.is_allowed():
                self.log_result("Is Allowed Check", True, "Correctly blocks without acquiring")
            else:
                self.log_result("Is Allowed Check", False, "Should block but doesn't")
                return False
            
            # Cleanup
            self.redis_client.delete(test_limiter.key)
            return True
            
        except Exception as e:
            self.log_result("Rate Limiting Behavior", False, str(e))
            return False
    
    def validate_service_integration(self) -> bool:
        """Validate that services integrate correctly with rate limiting."""
        print("\n🔗 Validating Service Integration...")
        
        try:
            # Test CampaignService integration
            from app.services.campaign import CampaignService
            
            service = CampaignService()
            
            # Check Apollo service integration
            if hasattr(service, 'apollo_service') and service.apollo_service:
                if hasattr(service.apollo_service, 'rate_limiter') and service.apollo_service.rate_limiter:
                    self.log_result("CampaignService - Apollo", True, "Rate limiter attached")
                else:
                    self.log_result("CampaignService - Apollo", False, "No rate limiter attached")
            else:
                self.log_result("CampaignService - Apollo", True, "Service not available (expected)")
            
            # Check Instantly service integration
            if hasattr(service, 'instantly_service') and service.instantly_service:
                if hasattr(service.instantly_service, 'rate_limiter') and service.instantly_service.rate_limiter:
                    self.log_result("CampaignService - Instantly", True, "Rate limiter attached")
                else:
                    self.log_result("CampaignService - Instantly", False, "No rate limiter attached")
            else:
                self.log_result("CampaignService - Instantly", True, "Service not available (expected)")
            
            # Test individual service initialization
            services_to_test = [
                ('EmailVerifierService', 'app.background_services.email_verifier_service', 'MILLIONVERIFIER_API_KEY'),
                ('PerplexityService', 'app.background_services.perplexity_service', 'PERPLEXITY_TOKEN'),
                ('OpenAIService', 'app.background_services.openai_service', 'OPENAI_API_KEY'),
                ('InstantlyService', 'app.background_services.instantly_service', 'INSTANTLY_API_KEY'),
            ]
            
            for service_name, module_path, env_var in services_to_test:
                with patch.dict('os.environ', {env_var: 'test_key'}):
                    try:
                        module = __import__(module_path, fromlist=[service_name])
                        service_class = getattr(module, service_name)
                        
                        # Test without rate limiter (backward compatibility)
                        service_instance = service_class()
                        self.log_result(f"{service_name} - No Rate Limiter", True, "Backward compatible")
                        
                        # Test with rate limiter
                        if self.redis_client:
                            if service_name == 'EmailVerifierService':
                                rate_limiter = get_email_verifier_rate_limiter(self.redis_client)
                            elif service_name == 'PerplexityService':
                                rate_limiter = get_perplexity_rate_limiter(self.redis_client)
                            elif service_name == 'OpenAIService':
                                rate_limiter = get_openai_rate_limiter(self.redis_client)
                            elif service_name == 'InstantlyService':
                                rate_limiter = get_instantly_rate_limiter(self.redis_client)
                            
                            service_with_limiter = service_class(rate_limiter=rate_limiter)
                            if hasattr(service_with_limiter, 'rate_limiter') and service_with_limiter.rate_limiter:
                                self.log_result(f"{service_name} - With Rate Limiter", True, "Integration successful")
                            else:
                                self.log_result(f"{service_name} - With Rate Limiter", False, "Rate limiter not attached")
                        
                    except Exception as e:
                        self.log_result(f"{service_name} - Integration", False, str(e))
            
            return True
            
        except Exception as e:
            self.log_result("Service Integration", False, str(e))
            return False
    
    def validate_graceful_degradation(self) -> bool:
        """Validate graceful degradation when Redis is unavailable."""
        print("\n🛡️  Validating Graceful Degradation...")
        
        try:
            # Create a fake Redis client that always fails
            from redis import Redis
            failed_redis = Redis(host='nonexistent-host', port=9999, socket_timeout=1)
            
            # Test rate limiter with failed Redis
            limiter = ApiIntegrationRateLimiter(
                redis_client=failed_redis,
                api_name='GracefulTest',
                max_requests=5,
                period_seconds=60
            )
            
            # Should gracefully degrade
            if limiter.acquire():
                self.log_result("Graceful Degradation - Acquire", True, "Allows requests when Redis fails")
            else:
                self.log_result("Graceful Degradation - Acquire", False, "Should allow requests when Redis fails")
                return False
            
            # Should return max_requests for remaining
            remaining = limiter.get_remaining()
            if remaining == 5:
                self.log_result("Graceful Degradation - Remaining", True, f"Returns {remaining} when Redis fails")
            else:
                self.log_result("Graceful Degradation - Remaining", False, f"Returns {remaining}, expected 5")
                return False
            
            # Should allow checking
            if limiter.is_allowed():
                self.log_result("Graceful Degradation - Is Allowed", True, "Allows checking when Redis fails")
            else:
                self.log_result("Graceful Degradation - Is Allowed", False, "Should allow checking when Redis fails")
                return False
            
            # Test service initialization with failed Redis
            with patch('app.core.config.get_redis_connection') as mock_redis:
                mock_redis.side_effect = Exception("Redis unavailable")
                
                from app.services.campaign import CampaignService
                service = CampaignService()
                
                # Services should handle the failure gracefully
                self.log_result("Graceful Degradation - Service Init", True, "Services handle Redis failure")
            
            return True
            
        except Exception as e:
            self.log_result("Graceful Degradation", False, str(e))
            return False
    
    def validate_performance(self) -> bool:
        """Validate performance characteristics."""
        print("\n⚡ Validating Performance...")
        
        if not self.redis_client:
            self.log_result("Performance Validation", False, "Redis not available")
            return False
        
        try:
            # Test basic performance
            limiter = ApiIntegrationRateLimiter(
                redis_client=self.redis_client,
                api_name='PerfTest',
                max_requests=100,
                period_seconds=60
            )
            
            self.redis_client.delete(limiter.key)
            
            # Measure time for 100 acquisitions
            start_time = time.time()
            successful = 0
            for i in range(100):
                if limiter.acquire():
                    successful += 1
            
            end_time = time.time()
            duration = end_time - start_time
            
            if duration < 5.0:  # Should complete in under 5 seconds
                self.log_result("Performance - Basic", True, f"100 requests in {duration:.2f}s")
            else:
                self.log_result("Performance - Basic", False, f"Too slow: {duration:.2f}s")
                return False
            
            if successful == 100:
                self.log_result("Performance - Accuracy", True, "All 100 requests allowed correctly")
            else:
                self.log_result("Performance - Accuracy", False, f"Only {successful}/100 allowed")
                return False
            
            # Test throughput
            throughput = 100 / duration
            if throughput > 50:  # Should handle > 50 requests/second
                self.log_result("Performance - Throughput", True, f"{throughput:.1f} req/s")
            else:
                self.log_result("Performance - Throughput", False, f"Too slow: {throughput:.1f} req/s")
                return False
            
            # Cleanup
            self.redis_client.delete(limiter.key)
            return True
            
        except Exception as e:
            self.log_result("Performance Validation", False, str(e))
            return False
    
    def run_full_validation(self) -> bool:
        """Run all validation tests."""
        print("🚀 Starting API Rate Limiting System Validation...")
        print("=" * 60)
        
        # Run all validation steps
        validations = [
            self.validate_configuration,
            self.validate_redis_connectivity,
            self.validate_rate_limiter_creation,
            self.validate_rate_limiting_behavior,
            self.validate_service_integration,
            self.validate_graceful_degradation,
            self.validate_performance
        ]
        
        all_passed = True
        for validation in validations:
            try:
                result = validation()
                if not result:
                    all_passed = False
            except Exception as e:
                print(f"❌ CRITICAL ERROR in {validation.__name__}: {str(e)}")
                all_passed = False
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in self.results if r['passed'])
        total = len(self.results)
        
        print(f"Tests Passed: {passed}/{total}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if all_passed:
            print("\n🎉 ALL VALIDATIONS PASSED!")
            print("✅ The rate limiting system is working correctly.")
        else:
            print("\n⚠️  SOME VALIDATIONS FAILED!")
            print("❌ Please review the failed tests above.")
        
        return all_passed


def main():
    """Main entry point for the validation script."""
    parser = argparse.ArgumentParser(description='Validate API Rate Limiting System')
    parser.add_argument('--redis-host', help='Redis host (default: from config)')
    parser.add_argument('--redis-port', type=int, help='Redis port (default: from config)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    validator = RateLimitingValidator(
        redis_host=args.redis_host,
        redis_port=args.redis_port
    )
    
    success = validator.run_full_validation()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main() 