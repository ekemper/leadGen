#!/usr/bin/env python3
"""
Validation script for OpenAI rate limiting configuration.

This script validates that the rate limiting configuration is properly set up
to prevent hitting OpenAI's token-per-minute (TPM) limits.
"""

import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.api_integration_rate_limiter import get_api_rate_limits
from redis import Redis

def validate_openai_rate_config():
    """Validate OpenAI rate limiting configuration."""
    print("🔍 Validating OpenAI Rate Limiting Configuration...")
    print("=" * 60)
    
    # Check configuration values
    requests_per_minute = settings.OPENAI_RATE_LIMIT_REQUESTS
    period_seconds = settings.OPENAI_RATE_LIMIT_PERIOD
    
    print(f"📊 Current Configuration:")
    print(f"   Requests per minute: {requests_per_minute}")
    print(f"   Period (seconds): {period_seconds}")
    
    # Calculate theoretical token usage
    avg_tokens_per_request = 400  # Conservative estimate based on logs
    max_tokens_per_request = 500  # High estimate
    
    theoretical_min_tokens = requests_per_minute * 200  # Minimum realistic usage
    theoretical_avg_tokens = requests_per_minute * avg_tokens_per_request
    theoretical_max_tokens = requests_per_minute * max_tokens_per_request
    
    print(f"\n🧮 Token Usage Calculations:")
    print(f"   Minimum tokens/minute: {theoretical_min_tokens}")
    print(f"   Average tokens/minute: {theoretical_avg_tokens}")
    print(f"   Maximum tokens/minute: {theoretical_max_tokens}")
    print(f"   OpenAI TPM limit: 10,000")
    
    # Validate against OpenAI limits
    openai_tpm_limit = 10000
    safety_margin = 0.25  # 25% safety margin
    safe_limit = openai_tpm_limit * (1 - safety_margin)
    
    print(f"\n🛡️  Safety Analysis:")
    print(f"   Safe token limit (75% of max): {safe_limit}")
    
    if theoretical_max_tokens <= safe_limit:
        print("   ✅ Configuration is SAFE - within limits")
        config_status = "SAFE"
    elif theoretical_avg_tokens <= safe_limit:
        print("   ⚠️  Configuration is MODERATE - monitor closely")
        config_status = "MODERATE"
    else:
        print("   ❌ Configuration is RISKY - likely to hit limits")
        config_status = "RISKY"
    
    # Recommendations
    print(f"\n💡 Recommendations:")
    if config_status == "SAFE":
        print("   Current configuration should prevent rate limit errors")
        print("   Monitor actual token usage to optimize further")
    elif config_status == "MODERATE":
        print("   Consider reducing to 12-13 requests/minute for better safety")
        print("   Implement token usage monitoring")
    else:
        print("   URGENT: Reduce requests/minute to prevent API failures")
        print("   Recommended: 10-12 requests/minute maximum")
    
    return config_status

def validate_redis_connection():
    """Validate Redis connection for rate limiting."""
    print("\n🔗 Validating Redis Connection...")
    print("=" * 40)
    
    try:
        redis_client = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
            socket_connect_timeout=5
        )
        
        # Test connection
        redis_client.ping()
        print("   ✅ Redis connection successful")
        
        # Test rate limiter key
        test_key = "test_openai_rate_limit"
        redis_client.set(test_key, "1", ex=60)
        value = redis_client.get(test_key)
        redis_client.delete(test_key)
        
        if value == "1":
            print("   ✅ Redis operations working correctly")
            return True
        else:
            print("   ❌ Redis operations failed")
            return False
            
    except Exception as e:
        print(f"   ❌ Redis connection failed: {e}")
        return False

def validate_configuration_loading():
    """Validate that rate limiting configuration loads correctly."""
    print("\n⚙️  Validating Configuration Loading...")
    print("=" * 45)
    
    try:
        api_limits = get_api_rate_limits()
        openai_config = api_limits.get('OpenAI', {})
        
        print(f"   OpenAI Max Requests: {openai_config.get('max_requests', 'NOT SET')}")
        print(f"   OpenAI Period: {openai_config.get('period_seconds', 'NOT SET')}")
        
        if (openai_config.get('max_requests') == settings.OPENAI_RATE_LIMIT_REQUESTS and
            openai_config.get('period_seconds') == settings.OPENAI_RATE_LIMIT_PERIOD):
            print("   ✅ Configuration loading correctly")
            return True
        else:
            print("   ❌ Configuration mismatch")
            return False
            
    except Exception as e:
        print(f"   ❌ Configuration loading failed: {e}")
        return False

def main():
    """Main validation function."""
    print("🚀 OpenAI Rate Limiting Validation")
    print("=" * 50)
    print("This script validates the new rate limiting configuration")
    print("to prevent OpenAI token-per-minute (TPM) limit issues.\n")
    
    # Run validations
    config_status = validate_openai_rate_config()
    redis_ok = validate_redis_connection()
    config_ok = validate_configuration_loading()
    
    # Summary
    print("\n📋 Validation Summary:")
    print("=" * 30)
    print(f"Rate Limit Config: {config_status}")
    print(f"Redis Connection: {'✅ OK' if redis_ok else '❌ FAILED'}")
    print(f"Config Loading: {'✅ OK' if config_ok else '❌ FAILED'}")
    
    if config_status == "SAFE" and redis_ok and config_ok:
        print("\n🎉 All validations passed! Rate limiting should work correctly.")
        return 0
    else:
        print("\n⚠️  Some validations failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    exit(main()) 