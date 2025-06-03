import os
import requests
from app.models.lead import Lead
from typing import Dict, Any, List, Optional
from app.core.logger import get_logger
from app.core.api_integration_rate_limiter import ApiIntegrationRateLimiter

logger = get_logger(__name__)

class PerplexityService:
    """
    Service for enriching leads using Perplexity AI.
    
    This service now supports rate limiting to prevent exceeding API limits
    and avoid IP blocking. Rate limiting is optional to maintain backward 
    compatibility with existing code.
    """

    API_URL = "https://api.perplexity.ai/chat/completions"
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds

    def __init__(self, rate_limiter: Optional[ApiIntegrationRateLimiter] = None):
        """
        Initialize the PerplexityService.
        
        Args:
            rate_limiter: Optional rate limiter for Perplexity API calls.
                         If not provided, no rate limiting will be applied.
        """
        self.token = os.getenv("PERPLEXITY_TOKEN")
        if not self.token:
            raise RuntimeError("PERPLEXITY_TOKEN environment variable is not set")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        self.rate_limiter = rate_limiter
        
        # Log rate limiting status for monitoring
        if self.rate_limiter:
            logger.info(
                f"PerplexityService initialized with rate limiting: "
                f"{self.rate_limiter.max_requests} requests per {self.rate_limiter.period_seconds}s",
                extra={'component': 'perplexity_service', 'rate_limiting': 'enabled'}
            )
        else:
            logger.info(
                "PerplexityService initialized without rate limiting",
                extra={'component': 'perplexity_service', 'rate_limiting': 'disabled'}
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
                        f"Rate limit exceeded for Perplexity API. "
                        f"Remaining requests: {remaining}. "
                        f"Try again in {self.rate_limiter.period_seconds} seconds."
                    )
                    logger.warning(
                        f"Rate limit exceeded for {operation}",
                        extra={
                            'component': 'perplexity_service',
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
                    extra={'component': 'perplexity_service', 'rate_limiter_error': str(rate_limit_error)}
                )
        return None

    def build_prompt(self, lead: Lead) -> Dict[str, Any]:
        """
        Build a prompt for Perplexity enrichment using lead details.
        Args:
            lead: Lead object
        Returns:
            dict: The prompt JSON with lead details filled in.
        Raises:
            ValueError: If any required prompt variable is missing.
        """
        if not lead:
            raise ValueError("Lead is required")

        # Map properties from the lead record
        first_name = getattr(lead, 'first_name', '')
        last_name = getattr(lead, 'last_name', '')
        # company_name is not a direct field, fallback to company
        company_name = getattr(lead, 'company_name', None) or getattr(lead, 'company', '')

        # Try to get headline from raw_data or fallback to title
        headline = ''
        if hasattr(lead, 'raw_data') and lead.raw_data:
            headline = lead.raw_data.get('headline')
        if not headline:
            headline = getattr(lead, 'title', '')

        # Log the extracted prompt variables
        logger.info(f"Prompt variables for lead {getattr(lead, 'id', None)}: first_name='{first_name}', last_name='{last_name}', headline='{headline}', company_name='{company_name}'", extra={'component': 'perplexity_service'})

        # Check for missing required properties
        missing = []
        if not first_name:
            missing.append('first_name')
        if not last_name:
            missing.append('last_name')
        if not headline:
            missing.append('headline')
        if not company_name:
            missing.append('company_name')
        if missing:
            error_msg = f"Missing required prompt variables: {', '.join(missing)} for lead {getattr(lead, 'id', None)}"
            logger.error(error_msg, extra={'component': 'perplexity_service'})
            raise ValueError(error_msg)

        prompt = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [
                {"role": "system", "content": "Be precise and concise."},
                {"role": "user", "content": f"{first_name} {last_name} who is the {headline} at {company_name}"}
            ],
            "temperature": 0.2,
            "top_p": 0.9,
            "search_domain_filter": ["perplexity.ai"],
            "return_images": False,
            "return_related_questions": False,
            "search_recency_filter": "month",
            "top_k": 0,
            "stream": False,
            "presence_penalty": 0,
            "frequency_penalty": 1
        }
        # Log the built prompt
        logger.info(f"Built Perplexity prompt for lead {getattr(lead, 'id', None)}: {prompt}", extra={'component': 'perplexity_service'})
        return prompt

    def enrich_lead(self, lead: Lead) -> Dict[str, Any]:
        """
        Enrich a single lead using Perplexity API.
        
        This method now includes rate limiting support to prevent exceeding
        API limits. If rate limiting is enabled and the limit is exceeded,
        the method will return an error response.
        
        Args:
            lead: Lead object to enrich
        Returns:
            dict: Enrichment results or error response
        """
        if not lead:
            raise ValueError("Lead is required")

        # Check rate limiting if enabled
        rate_limit_error = self._check_rate_limit(f"enrich_lead for lead {getattr(lead, 'id', None)}")
        if rate_limit_error:
            return rate_limit_error

        prompt = self.build_prompt(lead)
        
        for attempt in range(self.MAX_RETRIES):
            try:
                logger.info(f"Enriching lead {lead.id} (attempt {attempt + 1}/{self.MAX_RETRIES})", extra={'component': 'perplexity_service'})
                response = requests.post(self.API_URL, json=prompt, headers=self.headers, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                
                # Log rate limiting status for monitoring
                if self.rate_limiter:
                    remaining = self.rate_limiter.get_remaining()
                    logger.info(
                        f"Lead enrichment successful for lead {getattr(lead, 'id', None)}. Rate limiter remaining: {remaining}",
                        extra={
                            'component': 'perplexity_service',
                            'lead_id': getattr(lead, 'id', None),
                            'rate_limiter_remaining': remaining
                        }
                    )
                else:
                    logger.info(
                        f"Lead enrichment successful for lead {getattr(lead, 'id', None)}",
                        extra={'component': 'perplexity_service', 'lead_id': getattr(lead, 'id', None)}
                    )
                
                return result
                
            except requests.RequestException as e:
                error_msg = f"Perplexity API request failed for lead {lead.id}: {str(e)}"
                logger.error(error_msg, extra={'component': 'perplexity_service'})
                if attempt < self.MAX_RETRIES - 1:
                    continue
                return {'error': error_msg}
            except Exception as e:
                error_msg = f"Unexpected error enriching lead {lead.id}: {str(e)}"
                logger.error(error_msg, extra={'component': 'perplexity_service'})
                return {'error': error_msg} 