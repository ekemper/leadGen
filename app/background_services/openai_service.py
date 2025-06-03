import os
from typing import Optional, Dict, Any
from openai import OpenAI
from app.core.api_integration_rate_limiter import ApiIntegrationRateLimiter
from app.core.logger import get_logger
from app.models import Lead
from app.core.circuit_breaker import CircuitBreakerService, ThirdPartyService

logger = get_logger(__name__)

class OpenAIService:
    """
    Service for generating email copy using OpenAI's API.
    
    This service now supports rate limiting to prevent exceeding API limits
    and avoid IP blocking. Rate limiting is optional to maintain backward 
    compatibility with existing code.
    """

    def __init__(self, rate_limiter: Optional[ApiIntegrationRateLimiter] = None, circuit_breaker: Optional[CircuitBreakerService] = None):
        """
        Initialize the OpenAIService.
        
        Args:
            rate_limiter: Optional rate limiter for OpenAI API calls.
                         If not provided, no rate limiting will be applied.
            circuit_breaker: Optional circuit breaker for OpenAI API calls.
                           If not provided, no circuit breaking will be applied.
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        self.client = OpenAI(api_key=api_key)
        self.rate_limiter = rate_limiter
        self.circuit_breaker = circuit_breaker
        
        # Log rate limiting status for monitoring
        if self.rate_limiter:
            logger.info(
                f"OpenAIService initialized with rate limiting: "
                f"{self.rate_limiter.max_requests} requests per {self.rate_limiter.period_seconds}s",
                extra={'component': 'openai_service', 'rate_limiting': 'enabled'}
            )
        else:
            logger.info(
                "OpenAIService initialized without rate limiting",
                extra={'component': 'openai_service', 'rate_limiting': 'disabled'}
            )

    def _check_circuit_breaker(self, operation: str) -> Optional[dict]:
        """
        Check circuit breaker if enabled.
        
        Args:
            operation: The operation being performed for logging
            
        Returns:
            dict: Error response if circuit is open, None if allowed
        """
        if self.circuit_breaker:
            allowed, reason = self.circuit_breaker.should_allow_request(ThirdPartyService.OPENAI)
            if not allowed:
                error_msg = f"OpenAI API circuit breaker is open: {reason}"
                logger.warning(
                    f"Circuit breaker blocked {operation}",
                    extra={
                        'component': 'openai_service',
                        'circuit_breaker_open': True,
                        'reason': reason,
                        'operation': operation
                    }
                )
                return {
                    'status': 'circuit_breaker_open',
                    'error': error_msg,
                    'reason': reason
                }
        return None

    def _check_rate_limit(self, operation: str) -> Optional[dict]:
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
                        f"Rate limit exceeded for OpenAI API. "
                        f"Remaining requests: {remaining}. "
                        f"Try again in {self.rate_limiter.period_seconds} seconds."
                    )
                    logger.warning(
                        f"Rate limit exceeded for {operation}",
                        extra={
                            'component': 'openai_service',
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
                    extra={'component': 'openai_service', 'rate_limiter_error': str(rate_limit_error)}
                )
        return None

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """
        Check if an error is a rate limit error (429).
        
        Args:
            error: The exception to check
            
        Returns:
            bool: True if this is a rate limit error
        """
        error_str = str(error).lower()
        return (
            '429' in error_str or 
            'rate limit' in error_str or 
            'too many requests' in error_str or
            'rate_limit_exceeded' in error_str or
            'tpm' in error_str or  # Tokens per minute
            'rpm' in error_str    # Requests per minute
        )

    def _extract_rate_limit_details(self, error: Exception) -> dict:
        """
        Extract detailed information from OpenAI rate limit errors.
        
        Args:
            error: The rate limit exception
            
        Returns:
            dict: Details about the rate limit error
        """
        error_str = str(error)
        details = {'error_type': 'unknown_rate_limit'}
        
        # Check for TPM (Tokens Per Minute) limit
        if 'TPM' in error_str:
            details['error_type'] = 'tokens_per_minute'
            # Extract limit and usage if available
            import re
            tpm_match = re.search(r'Limit (\d+), Used (\d+), Requested (\d+)', error_str)
            if tpm_match:
                details['limit'] = int(tpm_match.group(1))
                details['used'] = int(tpm_match.group(2))
                details['requested'] = int(tpm_match.group(3))
        
        # Check for RPM (Requests Per Minute) limit
        elif 'RPM' in error_str:
            details['error_type'] = 'requests_per_minute'
        
        return details

    def generate_email_copy(self, lead: Lead, enrichment_data: Dict[str, Any]) -> dict:
        """
        Generate personalized email copy for a lead.
        
        This method now includes rate limiting support to prevent exceeding
        API limits. If rate limiting is enabled and the limit is exceeded,
        the method will return an error response.
        
        Args:
            lead: The lead to generate email copy for
            enrichment_data: Additional data about the lead
        Returns:
            The full OpenAI API response (dict) or error response
        """
        operation = f"generate_email_copy for lead {getattr(lead, 'id', None)}"
        
        # Check circuit breaker if enabled
        circuit_error = self._check_circuit_breaker(operation)
        if circuit_error:
            return circuit_error
        
        # Check rate limiting if enabled
        rate_limit_error = self._check_rate_limit(operation)
        if rate_limit_error:
            # Record rate limit as failure in circuit breaker
            if self.circuit_breaker:
                self.circuit_breaker.record_failure(
                    ThirdPartyService.OPENAI, 
                    rate_limit_error.get('error', 'Rate limited'), 
                    'rate_limit'
                )
            return rate_limit_error
        
        try:
            # Extract and log prompt variables
            first_name = getattr(lead, 'first_name', '')
            last_name = getattr(lead, 'last_name', '')
            company_name = getattr(lead, 'company_name', None) or getattr(lead, 'company', '')
            full_name = f"{first_name} {last_name}".strip()
            
            logger.info(
                f"Email copy prompt vars for lead {getattr(lead, 'id', None)}: first_name='{first_name}', last_name='{last_name}', company_name='{company_name}'", 
                extra={'component': 'openai_service', 'lead_id': getattr(lead, 'id', None)}
            )

            # Validate required fields
            missing = []
            if not first_name:
                missing.append('first_name')
            if not last_name:
                missing.append('last_name')
            if not company_name:
                missing.append('company_name')
            if missing:
                error_msg = f"Missing required prompt variables for email copy: {', '.join(missing)} for lead {getattr(lead, 'id', None)}"
                logger.error(
                    error_msg, 
                    extra={'component': 'openai_service', 'lead_id': getattr(lead, 'id', None), 'missing_fields': missing}
                )
                return {
                    'status': 'error',
                    'error': error_msg
                }

            # Extract enrichment content
            enrichment_content = ""
            if enrichment_data and 'choices' in enrichment_data:
                enrichment_content = enrichment_data['choices'][0]['message']['content']

            prompt = f"""Write a personalized email to {full_name} at {company_name}.

Enrichment Information:
{enrichment_content}

Lead Information:
- Name: {full_name}
- Company: {company_name}
- Role: {getattr(lead, 'title', 'Unknown')}

Write a professional, personalized email that:
1. Shows understanding of their business
2. Offers specific value
3. Has a clear call to action
4. Is concise and engaging

Email:"""

            logger.info(
                f"Built email copy prompt for lead {getattr(lead, 'id', None)}", 
                extra={'component': 'openai_service', 'lead_id': getattr(lead, 'id', None)}
            )

            # Call OpenAI API (openai>=1.0.0 interface)
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a professional email copywriter."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )

            result = response.model_dump()
            
            # Record success in circuit breaker
            if self.circuit_breaker:
                self.circuit_breaker.record_success(ThirdPartyService.OPENAI)
            
            # Log rate limiting status for monitoring
            if self.rate_limiter:
                remaining = self.rate_limiter.get_remaining()
                logger.info(
                    f"Email copy generation successful for lead {getattr(lead, 'id', None)}. Rate limiter remaining: {remaining}",
                    extra={
                        'component': 'openai_service',
                        'lead_id': getattr(lead, 'id', None),
                        'rate_limiter_remaining': remaining
                    }
                )
            else:
                logger.info(
                    f"Email copy generation successful for lead {getattr(lead, 'id', None)}",
                    extra={'component': 'openai_service', 'lead_id': getattr(lead, 'id', None)}
                )
            
            return result
            
        except Exception as e:
            error_msg = f"Error generating email copy for lead {getattr(lead, 'id', None)}: {str(e)}"
            logger.error(
                error_msg, 
                extra={'component': 'openai_service', 'lead_id': getattr(lead, 'id', None), 'error': str(e)}
            )
            
            # Check if this is a rate limit error and handle appropriately
            if self._is_rate_limit_error(e):
                rate_limit_details = self._extract_rate_limit_details(e)
                
                logger.warning(
                    f"Detected OpenAI rate limit error for lead {getattr(lead, 'id', None)}: {str(e)}",
                    extra={
                        'component': 'openai_service', 
                        'lead_id': getattr(lead, 'id', None), 
                        'error_type': 'rate_limit',
                        'rate_limit_details': rate_limit_details
                    }
                )
                
                # Record rate limit failure in circuit breaker with detailed info
                if self.circuit_breaker:
                    error_context = f"{rate_limit_details.get('error_type', 'rate_limit')}: {str(e)}"
                    self.circuit_breaker.record_failure(ThirdPartyService.OPENAI, error_context, 'rate_limit')
                
                # Return specific rate limit error with details
                return {
                    'status': 'rate_limited',
                    'error': str(e),
                    'error_type': 'openai_api_rate_limit',
                    'rate_limit_details': rate_limit_details
                }
            else:
                # Record general failure in circuit breaker
                if self.circuit_breaker:
                    self.circuit_breaker.record_failure(ThirdPartyService.OPENAI, str(e), 'exception')
                
                # Return generic error
                return {
                    'status': 'error',
                    'error': str(e)
                } 