import os
import requests
import time
import uuid
from datetime import datetime
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
    
    Enhanced with comprehensive timing and request logging for debugging
    rate limiting issues and analyzing request patterns.
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

    def _log_request_attempt(self, lead_id: str, attempt_number: int, correlation_id: str, 
                           rate_limiter_decision: str, rate_limiter_remaining: int, 
                           time_since_last_request: Optional[float]) -> None:
        """
        Log detailed timing information for each request attempt.
        
        Args:
            lead_id: ID of the lead being enriched
            attempt_number: Current attempt number (1-3)
            correlation_id: Correlation ID for tracking this request
            rate_limiter_decision: Whether request was allowed or denied
            rate_limiter_remaining: Number of remaining requests in rate limiter
            time_since_last_request: Seconds since last request, None if first request
        """
        current_time = datetime.utcnow()
        
        logger.info(
            f"perplexity timing test log - Request Attempt: "
            f"correlation_id={correlation_id}, "
            f"timestamp={current_time.isoformat()}Z, "
            f"time_since_last_request={time_since_last_request}, "
            f"rate_limiter_decision={rate_limiter_decision}, "
            f"rate_limiter_remaining={rate_limiter_remaining}, "
            f"lead_id={lead_id}, "
            f"attempt_number={attempt_number}",
            extra={
                'component': 'perplexity_service',
                'log_type': 'timing_test',
                'event': 'request_attempt',
                'correlation_id': correlation_id,
                'lead_id': lead_id,
                'attempt_number': attempt_number,
                'rate_limiter_decision': rate_limiter_decision,
                'rate_limiter_remaining': rate_limiter_remaining,
                'time_since_last_request': time_since_last_request,
                'timestamp_iso': current_time.isoformat() + 'Z'
            }
        )

    def _log_request_response(self, correlation_id: str, response_status: str, 
                            response_time_ms: float, api_response_code: Optional[int] = None,
                            error_details: Optional[str] = None) -> None:
        """
        Log detailed response information for each request.
        
        Args:
            correlation_id: Correlation ID for tracking this request
            response_status: Status of the response (success, error, rate_limited)
            response_time_ms: Response time in milliseconds
            api_response_code: HTTP response code if available
            error_details: Error details if applicable
        """
        logger.info(
            f"perplexity timing test log - Request Response: "
            f"correlation_id={correlation_id}, "
            f"response_status={response_status}, "
            f"response_time_ms={response_time_ms:.2f}, "
            f"api_response_code={api_response_code}, "
            f"error_details={error_details}",
            extra={
                'component': 'perplexity_service',
                'log_type': 'timing_test',
                'event': 'request_response',
                'correlation_id': correlation_id,
                'response_status': response_status,
                'response_time_ms': response_time_ms,
                'api_response_code': api_response_code,
                'error_details': error_details
            }
        )

    def _check_rate_limit(self, operation: str, lead_id: str, correlation_id: str, attempt_number: int) -> dict:
        """
        Check rate limiting if enabled with comprehensive timing logging.
        
        Args:
            operation: The operation being performed for logging
            lead_id: ID of the lead being processed
            correlation_id: Correlation ID for tracking this request
            attempt_number: Current attempt number
            
        Returns:
            dict: Error response if rate limited, None if allowed
        """
        if self.rate_limiter:
            try:
                # Get timing information before checking rate limit
                time_since_last_request = self.rate_limiter.get_time_since_last_request()
                
                # Check if request is allowed
                is_allowed = self.rate_limiter.acquire()
                remaining = self.rate_limiter.get_remaining()
                
                # Log the attempt with timing information
                rate_limiter_decision = "allowed" if is_allowed else "denied"
                self._log_request_attempt(
                    lead_id=lead_id,
                    attempt_number=attempt_number,
                    correlation_id=correlation_id,
                    rate_limiter_decision=rate_limiter_decision,
                    rate_limiter_remaining=remaining,
                    time_since_last_request=time_since_last_request
                )
                
                if not is_allowed:
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
                            'operation': operation,
                            'correlation_id': correlation_id,
                            'time_since_last_request': time_since_last_request
                        }
                    )
                    
                    # Log the rate limit response
                    self._log_request_response(
                        correlation_id=correlation_id,
                        response_status="rate_limited",
                        response_time_ms=0.0,
                        error_details=error_msg
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
                    extra={
                        'component': 'perplexity_service', 
                        'rate_limiter_error': str(rate_limit_error),
                        'correlation_id': correlation_id
                    }
                )
                
                # Log attempt without rate limiter
                self._log_request_attempt(
                    lead_id=lead_id,
                    attempt_number=attempt_number,
                    correlation_id=correlation_id,
                    rate_limiter_decision="error_fallback",
                    rate_limiter_remaining=-1,
                    time_since_last_request=None
                )
        else:
            # No rate limiter configured - log attempt without timing
            self._log_request_attempt(
                lead_id=lead_id,
                attempt_number=attempt_number,
                correlation_id=correlation_id,
                rate_limiter_decision="no_limiter",
                rate_limiter_remaining=-1,
                time_since_last_request=None
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
        Enrich a single lead using Perplexity API with comprehensive timing logging.
        
        This method now includes detailed timing logging to track each request attempt,
        rate limiter decisions, and response details for debugging rate limiting issues.
        
        Args:
            lead: Lead object to enrich
        Returns:
            dict: Enrichment results or error response
        """
        if not lead:
            raise ValueError("Lead is required")

        # Generate correlation ID for tracking this request across logs
        correlation_id = str(uuid.uuid4())
        lead_id = str(getattr(lead, 'id', 'unknown'))
        
        logger.info(
            f"Starting lead enrichment for lead {lead_id} with correlation_id {correlation_id}",
            extra={
                'component': 'perplexity_service',
                'correlation_id': correlation_id,
                'lead_id': lead_id
            }
        )

        prompt = self.build_prompt(lead)
        
        for attempt in range(self.MAX_RETRIES):
            attempt_number = attempt + 1
            
            # Check rate limiting with comprehensive logging
            rate_limit_error = self._check_rate_limit(
                f"enrich_lead for lead {lead_id}", 
                lead_id, 
                correlation_id, 
                attempt_number
            )
            if rate_limit_error:
                return rate_limit_error

            try:
                logger.info(
                    f"Making Perplexity API request for lead {lead_id} "
                    f"(attempt {attempt_number}/{self.MAX_RETRIES}, correlation_id: {correlation_id})",
                    extra={
                        'component': 'perplexity_service',
                        'correlation_id': correlation_id,
                        'lead_id': lead_id,
                        'attempt_number': attempt_number
                    }
                )
                
                # Record start time for response timing
                request_start_time = time.time()
                
                response = requests.post(self.API_URL, json=prompt, headers=self.headers, timeout=30)
                
                # Calculate response time
                response_time_ms = (time.time() - request_start_time) * 1000
                
                response.raise_for_status()
                result = response.json()
                
                # Log successful response
                self._log_request_response(
                    correlation_id=correlation_id,
                    response_status="success",
                    response_time_ms=response_time_ms,
                    api_response_code=response.status_code
                )
                
                # Log rate limiting status for monitoring
                if self.rate_limiter:
                    remaining = self.rate_limiter.get_remaining()
                    logger.info(
                        f"Lead enrichment successful for lead {lead_id}. "
                        f"Rate limiter remaining: {remaining}, correlation_id: {correlation_id}",
                        extra={
                            'component': 'perplexity_service',
                            'lead_id': lead_id,
                            'rate_limiter_remaining': remaining,
                            'correlation_id': correlation_id,
                            'response_time_ms': response_time_ms
                        }
                    )
                else:
                    logger.info(
                        f"Lead enrichment successful for lead {lead_id}, correlation_id: {correlation_id}",
                        extra={
                            'component': 'perplexity_service',
                            'lead_id': lead_id,
                            'correlation_id': correlation_id,
                            'response_time_ms': response_time_ms
                        }
                    )
                
                return result
                
            except requests.RequestException as e:
                # Calculate response time even for failed requests
                response_time_ms = (time.time() - request_start_time) * 1000 if 'request_start_time' in locals() else 0.0
                
                error_msg = f"Perplexity API request failed for lead {lead_id}: {str(e)}"
                
                # Extract status code if available
                api_response_code = None
                if hasattr(e, 'response') and e.response is not None:
                    api_response_code = e.response.status_code
                
                # Log failed response
                self._log_request_response(
                    correlation_id=correlation_id,
                    response_status="error",
                    response_time_ms=response_time_ms,
                    api_response_code=api_response_code,
                    error_details=str(e)
                )
                
                logger.error(
                    f"{error_msg} (correlation_id: {correlation_id}, attempt: {attempt_number})",
                    extra={
                        'component': 'perplexity_service',
                        'correlation_id': correlation_id,
                        'lead_id': lead_id,
                        'attempt_number': attempt_number,
                        'api_response_code': api_response_code,
                        'response_time_ms': response_time_ms
                    }
                )
                
                if attempt < self.MAX_RETRIES - 1:
                    continue
                return {'error': error_msg}
                
            except Exception as e:
                # Calculate response time even for unexpected errors
                response_time_ms = (time.time() - request_start_time) * 1000 if 'request_start_time' in locals() else 0.0
                
                error_msg = f"Unexpected error enriching lead {lead_id}: {str(e)}"
                
                # Log unexpected error
                self._log_request_response(
                    correlation_id=correlation_id,
                    response_status="error",
                    response_time_ms=response_time_ms,
                    error_details=str(e)
                )
                
                logger.error(
                    f"{error_msg} (correlation_id: {correlation_id}, attempt: {attempt_number})",
                    extra={
                        'component': 'perplexity_service',
                        'correlation_id': correlation_id,
                        'lead_id': lead_id,
                        'attempt_number': attempt_number,
                        'response_time_ms': response_time_ms
                    }
                )
                return {'error': error_msg} 