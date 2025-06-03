import os
import requests
from typing import Optional

from app.core.logger import get_logger
from app.core.api_integration_rate_limiter import ApiIntegrationRateLimiter

logger = get_logger(__name__)

class InstantlyService:
    """
    Service for integrating with Instantly API to create leads.
    
    This service now supports rate limiting to prevent exceeding API limits
    and avoid IP blocking. Rate limiting is optional to maintain backward 
    compatibility with existing code.
    """
    API_URL = "https://api.instantly.ai/api/v2/leads"
    API_CAMPAIGN_URL = "https://api.instantly.ai/api/v2/campaigns"

    def __init__(self, rate_limiter: Optional[ApiIntegrationRateLimiter] = None):
        """
        Initialize the InstantlyService.
        
        Args:
            rate_limiter: Optional rate limiter for Instantly API calls.
                         If not provided, no rate limiting will be applied.
        """
        self.api_key = os.getenv("INSTANTLY_API_KEY")
        if not self.api_key:
            raise ValueError("INSTANTLY_API_KEY environment variable is not set")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.rate_limiter = rate_limiter
        
        # Log rate limiting status for monitoring
        if self.rate_limiter:
            logger.info(
                f"InstantlyService initialized with rate limiting: "
                f"{self.rate_limiter.max_requests} requests per {self.rate_limiter.period_seconds}s",
                extra={'component': 'instantly_service', 'rate_limiting': 'enabled'}
            )
        else:
            logger.info(
                "InstantlyService initialized without rate limiting",
                extra={'component': 'instantly_service', 'rate_limiting': 'disabled'}
            )

    def _check_rate_limit(self, operation: str) -> dict:
        """
        Check rate limiting if enabled.
        
        Args:
            operation: The operation being performed for logging
            
        Returns:
            dict: Error response if rate limited, None if allowed
        """
        if self.rate_limiter:
            try:
                if not self.rate_limiter.acquire():
                    remaining = self.rate_limiter.get_remaining()
                    error_msg = (
                        f"Rate limit exceeded for Instantly API. "
                        f"Remaining requests: {remaining}. "
                        f"Try again in {self.rate_limiter.period_seconds} seconds."
                    )
                    logger.warning(
                        f"Rate limit exceeded for {operation}",
                        extra={
                            'component': 'instantly_service',
                            'rate_limit_exceeded': True,
                            'remaining_requests': remaining,
                            'operation': operation
                        }
                    )
                    return {
                        'status': 'rate_limited',
                        'error': error_msg,
                        'remaining_requests': remaining,
                        'retry_after_seconds': self.rate_limiter.period_seconds
                    }
            except Exception as rate_limit_error:
                # If rate limiter fails (e.g., Redis unavailable), log and continue
                logger.warning(
                    f"Rate limiter error, proceeding without rate limiting: {rate_limit_error}",
                    extra={'component': 'instantly_service', 'rate_limiter_error': str(rate_limit_error)}
                )
        return None

    def create_lead(self, campaign_id, email, first_name, personalization):
        """
        Create a lead in Instantly campaign.
        
        This method now includes rate limiting support to prevent exceeding
        API limits. If rate limiting is enabled and the limit is exceeded,
        the method will return an error response.
        """
        # Check rate limiting if enabled
        rate_limit_error = self._check_rate_limit(f"create_lead for {email}")
        if rate_limit_error:
            return rate_limit_error
        
        payload = {
            "campaign": campaign_id,
            "email": email,
            "firstName": first_name,
            "personalization": personalization
        }
        try:
            logger.info(
                f"Creating Instantly lead for {email} in campaign {campaign_id}",
                extra={'component': 'instantly_service', 'email': email, 'campaign_id': campaign_id}
            )
            
            response = requests.post(self.API_URL, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            # Log rate limiting status for monitoring
            if self.rate_limiter:
                remaining = self.rate_limiter.get_remaining()
                logger.info(
                    f"Successfully created Instantly lead for {email}. Rate limiter remaining: {remaining}",
                    extra={
                        'component': 'instantly_service',
                        'email': email,
                        'campaign_id': campaign_id,
                        'rate_limiter_remaining': remaining
                    }
                )
            else:
                logger.info(
                    f"Successfully created Instantly lead for {email} in campaign {campaign_id}",
                    extra={'component': 'instantly_service', 'email': email, 'campaign_id': campaign_id}
                )
            
            return result
            
        except requests.RequestException as e:
            logger.error(
                f"Error creating Instantly lead for {email}: {str(e)}",
                extra={'component': 'instantly_service', 'email': email, 'error': str(e)}
            )
            return {"error": str(e), "payload": payload}

    def create_campaign(self, name, schedule_name="My Schedule", timing_from="09:00", timing_to="17:00", days=None, timezone="Etc/GMT+12"):
        """
        Create a new campaign in Instantly.
        
        This method now includes rate limiting support to prevent exceeding
        API limits. If rate limiting is enabled and the limit is exceeded,
        the method will return an error response.
        """
        # Check rate limiting if enabled
        rate_limit_error = self._check_rate_limit(f"create_campaign '{name}'")
        if rate_limit_error:
            return rate_limit_error
        
        # Always use only Monday for the days property
        payload = {
            "name": name,
            "campaign_schedule": {
                "schedules": [
                    {
                        "name": schedule_name,
                        "timing": {
                            "from": timing_from,
                            "to": timing_to
                        },
                        "days": {"monday": True},
                        "timezone": timezone
                    }
                ]
            }
        }
        try:
            logger.info(
                f"Creating Instantly campaign '{name}'",
                extra={'component': 'instantly_service', 'campaign_name': name}
            )
            
            response = requests.post(self.API_CAMPAIGN_URL, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            # Log rate limiting status for monitoring
            if self.rate_limiter:
                remaining = self.rate_limiter.get_remaining()
                logger.info(
                    f"Successfully created Instantly campaign '{name}'. Rate limiter remaining: {remaining}",
                    extra={
                        'component': 'instantly_service',
                        'campaign_name': name,
                        'campaign_id': result.get('id'),
                        'rate_limiter_remaining': remaining
                    }
                )
            else:
                logger.info(
                    f"Successfully created Instantly campaign '{name}' with response: {result}",
                    extra={'component': 'instantly_service', 'campaign_name': name, 'campaign_id': result.get('id')}
                )
            
            return result
            
        except requests.RequestException as e:
            logger.error(
                f"Error creating Instantly campaign '{name}': {str(e)}",
                extra={'component': 'instantly_service', 'campaign_name': name, 'error': str(e)}
            )
            return {"error": str(e), "payload": payload}

    def get_campaign_analytics_overview(self, campaign_id, start_date=None, end_date=None, campaign_status=None):
        """
        Fetch campaign analytics overview from Instantly API.
        
        This method now includes rate limiting support to prevent exceeding
        API limits. If rate limiting is enabled and the limit is exceeded,
        the method will return an error response.
        
        :param campaign_id: The Instantly campaign ID (string)
        :param start_date: Optional start date (YYYY-MM-DD)
        :param end_date: Optional end date (YYYY-MM-DD)
        :param campaign_status: Optional campaign status (string or int)
        :return: dict (API response or error)
        """
        # Check rate limiting if enabled
        rate_limit_error = self._check_rate_limit(f"get_campaign_analytics_overview for {campaign_id}")
        if rate_limit_error:
            return rate_limit_error
        
        url = "https://api.instantly.ai/api/v2/campaigns/analytics/overview"
        query = {
            "id": campaign_id,
        }
        if start_date:
            query["start_date"] = start_date
        if end_date:
            query["end_date"] = end_date
        if campaign_status is not None:
            query["campaign_status"] = str(campaign_status)
            
        try:
            logger.info(
                f"Fetching Instantly analytics overview for campaign {campaign_id}",
                extra={'component': 'instantly_service', 'campaign_id': campaign_id}
            )
            
            response = requests.get(url, headers=self.headers, params=query, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            # Log rate limiting status for monitoring
            if self.rate_limiter:
                remaining = self.rate_limiter.get_remaining()
                logger.info(
                    f"Fetched Instantly analytics overview for campaign {campaign_id}. Rate limiter remaining: {remaining}",
                    extra={
                        'component': 'instantly_service',
                        'campaign_id': campaign_id,
                        'rate_limiter_remaining': remaining
                    }
                )
            else:
                logger.info(
                    f"Fetched Instantly analytics overview for campaign {campaign_id}: {result}",
                    extra={'component': 'instantly_service', 'campaign_id': campaign_id}
                )
            
            return result
            
        except requests.RequestException as e:
            logger.error(
                f"Error fetching Instantly analytics overview for campaign {campaign_id}: {str(e)}",
                extra={'component': 'instantly_service', 'campaign_id': campaign_id, 'error': str(e)}
            )
            return {"error": str(e), "query": query} 