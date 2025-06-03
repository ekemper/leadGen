from typing import Generator
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from redis import Redis

from app.core.database import get_db
from app.core.config import get_redis_connection
from app.core.api_integration_rate_limiter import ApiIntegrationRateLimiter, get_api_rate_limits
from app.services.auth_service import AuthService
from app.models.user import User


# Redis dependencies
def get_redis_client() -> Redis:
    """
    Dependency to provide Redis client for rate limiting and caching.
    
    This dependency creates a Redis connection using the application configuration.
    If Redis is unavailable, the connection will be handled gracefully by the
    rate limiter's built-in error handling.
    
    Returns:
        Redis: A Redis client instance configured from application settings
        
    Raises:
        HTTPException: If Redis connection cannot be established
    """
    try:
        return get_redis_connection()
    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Redis service unavailable: {str(e)}"
        )


# Rate Limiter dependencies
def get_email_verifier_rate_limiter(redis_client: Redis) -> ApiIntegrationRateLimiter:
    """
    Get MillionVerifier API rate limiter (can be called directly or as dependency).
    
    Args:
        redis_client: Redis client instance
        
    Returns:
        ApiIntegrationRateLimiter: Rate limiter configured for MillionVerifier API
    """
    limits = get_api_rate_limits()
    config = limits['MillionVerifier']
    return ApiIntegrationRateLimiter(
        redis_client=redis_client,
        api_name='MillionVerifier',
        max_requests=config['max_requests'],
        period_seconds=config['period_seconds']
    )

def get_millionverifier_rate_limiter(redis_client: Redis = Depends(get_redis_client)) -> ApiIntegrationRateLimiter:
    """
    Dependency to provide MillionVerifier API rate limiter.
    
    Args:
        redis_client: Redis client from dependency injection
        
    Returns:
        ApiIntegrationRateLimiter: Rate limiter configured for MillionVerifier API
    """
    return get_email_verifier_rate_limiter(redis_client)


def get_apollo_rate_limiter(redis_client: Redis) -> ApiIntegrationRateLimiter:
    """
    Get Apollo API rate limiter (can be called directly or as dependency).
    
    Args:
        redis_client: Redis client instance
        
    Returns:
        ApiIntegrationRateLimiter: Rate limiter configured for Apollo API
    """
    limits = get_api_rate_limits()
    config = limits['Apollo']
    return ApiIntegrationRateLimiter(
        redis_client=redis_client,
        api_name='Apollo',
        max_requests=config['max_requests'],
        period_seconds=config['period_seconds']
    )

def get_apollo_rate_limiter_dependency(redis_client: Redis = Depends(get_redis_client)) -> ApiIntegrationRateLimiter:
    """
    Dependency to provide Apollo API rate limiter.
    
    Args:
        redis_client: Redis client from dependency injection
        
    Returns:
        ApiIntegrationRateLimiter: Rate limiter configured for Apollo API
    """
    return get_apollo_rate_limiter(redis_client)


def get_instantly_rate_limiter(redis_client: Redis) -> ApiIntegrationRateLimiter:
    """
    Get Instantly API rate limiter (can be called directly or as dependency).
    
    Args:
        redis_client: Redis client instance
        
    Returns:
        ApiIntegrationRateLimiter: Rate limiter configured for Instantly API
    """
    limits = get_api_rate_limits()
    config = limits['Instantly']
    return ApiIntegrationRateLimiter(
        redis_client=redis_client,
        api_name='Instantly',
        max_requests=config['max_requests'],
        period_seconds=config['period_seconds']
    )

def get_instantly_rate_limiter_dependency(redis_client: Redis = Depends(get_redis_client)) -> ApiIntegrationRateLimiter:
    """
    Dependency to provide Instantly API rate limiter.
    
    Args:
        redis_client: Redis client from dependency injection
        
    Returns:
        ApiIntegrationRateLimiter: Rate limiter configured for Instantly API
    """
    return get_instantly_rate_limiter(redis_client)


def get_openai_rate_limiter(redis_client: Redis) -> ApiIntegrationRateLimiter:
    """
    Get OpenAI API rate limiter (can be called directly or as dependency).
    
    Args:
        redis_client: Redis client instance
        
    Returns:
        ApiIntegrationRateLimiter: Rate limiter configured for OpenAI API
    """
    limits = get_api_rate_limits()
    config = limits['OpenAI']
    return ApiIntegrationRateLimiter(
        redis_client=redis_client,
        api_name='OpenAI',
        max_requests=config['max_requests'],
        period_seconds=config['period_seconds']
    )

def get_openai_rate_limiter_dependency(redis_client: Redis = Depends(get_redis_client)) -> ApiIntegrationRateLimiter:
    """
    Dependency to provide OpenAI API rate limiter.
    
    Args:
        redis_client: Redis client from dependency injection
        
    Returns:
        ApiIntegrationRateLimiter: Rate limiter configured for OpenAI API
    """
    return get_openai_rate_limiter(redis_client)


def get_perplexity_rate_limiter(redis_client: Redis) -> ApiIntegrationRateLimiter:
    """
    Get Perplexity API rate limiter (can be called directly or as dependency).
    
    Args:
        redis_client: Redis client instance
        
    Returns:
        ApiIntegrationRateLimiter: Rate limiter configured for Perplexity API
    """
    limits = get_api_rate_limits()
    config = limits['Perplexity']
    return ApiIntegrationRateLimiter(
        redis_client=redis_client,
        api_name='Perplexity',
        max_requests=config['max_requests'],
        period_seconds=config['period_seconds']
    )

def get_perplexity_rate_limiter_dependency(redis_client: Redis = Depends(get_redis_client)) -> ApiIntegrationRateLimiter:
    """
    Dependency to provide Perplexity API rate limiter.
    
    Args:
        redis_client: Redis client from dependency injection
        
    Returns:
        ApiIntegrationRateLimiter: Rate limiter configured for Perplexity API
    """
    return get_perplexity_rate_limiter(redis_client)


def get_rate_limiter_for_service(service_name: str, redis_client: Redis = Depends(get_redis_client)) -> ApiIntegrationRateLimiter:
    """
    Generic dependency to provide rate limiter for any service.
    
    This is a utility dependency that can create a rate limiter for any configured service.
    Useful for dynamic service selection or testing scenarios.
    
    Args:
        service_name: Name of the service (must be in configured rate limits)
        redis_client: Redis client from dependency injection
        
    Returns:
        ApiIntegrationRateLimiter: Rate limiter configured for the specified service
        
    Raises:
        HTTPException: If service_name is not configured
    """
    limits = get_api_rate_limits()
    if service_name not in limits:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Service '{service_name}' is not configured for rate limiting. Available services: {list(limits.keys())}"
        )
    
    config = limits[service_name]
    return ApiIntegrationRateLimiter(
        redis_client=redis_client,
        api_name=service_name,
        max_requests=config['max_requests'],
        period_seconds=config['period_seconds']
    )


# Auth dependencies
security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to get current authenticated user."""
    auth_service = AuthService()
    return auth_service.get_current_user(credentials.credentials, db)

def get_current_user_from_middleware(request: Request) -> User:
    """Dependency to get current user from middleware state."""
    if not hasattr(request.state, 'current_user'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    return request.state.current_user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to get current active user (can be extended with user status checks)."""
    return current_user 