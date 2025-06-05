"""
Circuit Breaker Service

This module provides circuit breaker functionality for third-party services
to handle failures gracefully and prevent cascading failures.

SIMPLIFIED VERSION:
- Only OPEN/CLOSED states (no HALF_OPEN)
- Global circuit breaker state (not service-specific)
- Manual-only closing via frontend
- Any service error immediately opens circuit
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum
from redis import Redis
from app.core.logger import get_logger

logger = get_logger(__name__)

class CircuitState(str, Enum):
    CLOSED = "closed"    # Normal operation
    OPEN = "open"       # Failing, requests blocked
    # HALF_OPEN removed - simplified to only OPEN/CLOSED

# Keep ThirdPartyService enum for backward compatibility during transition
class ThirdPartyService(str, Enum):
    PERPLEXITY = "perplexity"
    OPENAI = "openai" 
    APOLLO = "apollo"
    INSTANTLY = "instantly"
    MILLIONVERIFIER = "millionverifier"

class CircuitBreakerService:
    """
    Simplified circuit breaker with global state management.
    
    Features:
    - Only OPEN/CLOSED states
    - Global circuit breaker (not service-specific)
    - Manual-only closing via API
    - Any failure immediately opens circuit
    - Job pause/resume on state changes
    """
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        # Simplified - no failure thresholds or recovery timeouts
        
    def _get_global_circuit_key(self) -> str:
        """Get Redis key for global circuit breaker state."""
        return "circuit_breaker:global"
    
    def get_global_circuit_state(self) -> CircuitState:
        """Get current global circuit state."""
        try:
            circuit_data = self.redis.get(self._get_global_circuit_key())
            if not circuit_data:
                return CircuitState.CLOSED
            
            data = json.loads(circuit_data)
            state = CircuitState(data.get('state', CircuitState.CLOSED))
            return state
        except Exception as e:
            logger.error(f"Error getting global circuit state: {e}")
            return CircuitState.CLOSED
    
    def _set_global_circuit_state(self, state: CircuitState, metadata: Optional[Dict] = None):
        """Set global circuit breaker state with optional metadata."""
        try:
            circuit_data = {
                'state': state.value,
                'opened_at': datetime.utcnow().isoformat() if state == CircuitState.OPEN else None,
                'closed_at': datetime.utcnow().isoformat() if state == CircuitState.CLOSED else None,
                'metadata': metadata or {}
            }
            
            circuit_key = self._get_global_circuit_key()
            # Store with longer TTL since this is global state
            self.redis.setex(circuit_key, 86400, json.dumps(circuit_data))  # 24 hours
            
            logger.info(f"Global circuit breaker state changed to: {state.value}")
            
        except Exception as e:
            logger.error(f"Error setting global circuit state: {e}")

    def record_failure(self, error: str, error_type: str = "unknown") -> bool:
        """
        Record a failure and immediately open circuit breaker.
        Simplified: any failure opens circuit immediately.
        """
        try:
            metadata = {
                'last_error': error,
                'error_type': error_type,
                'failed_at': datetime.utcnow().isoformat()
            }
            
            # Immediately open circuit on any failure
            current_state = self.get_global_circuit_state()
            if current_state == CircuitState.CLOSED:
                self._set_global_circuit_state(CircuitState.OPEN, metadata)
                self._handle_circuit_opened(error)
                return True
            
            # Already open, just update metadata
            self._set_global_circuit_state(CircuitState.OPEN, metadata)
            return False
            
        except Exception as e:
            logger.error(f"Error recording failure: {e}")
            return False

    def record_success(self):
        """
        Record a success. 
        Simplified: success does NOT automatically close circuit.
        Only manual closing is allowed.
        """
        try:
            # Log success but don't change state
            logger.debug("Service call succeeded, but circuit remains in current state")
            
            # Update metadata to track last success
            current_state = self.get_global_circuit_state()
            if current_state == CircuitState.OPEN:
                circuit_data = self.redis.get(self._get_global_circuit_key())
                if circuit_data:
                    data = json.loads(circuit_data)
                    metadata = data.get('metadata', {})
                    metadata['last_success'] = datetime.utcnow().isoformat()
                    self._set_global_circuit_state(CircuitState.OPEN, metadata)
                    
        except Exception as e:
            logger.error(f"Error recording success: {e}")

    def manually_close_circuit(self):
        """
        Manually close the circuit breaker.
        This is the ONLY way to close the circuit.
        """
        try:
            current_state = self.get_global_circuit_state()
            if current_state == CircuitState.OPEN:
                metadata = {
                    'manually_closed_at': datetime.utcnow().isoformat(),
                    'closed_by': 'manual_api_call'
                }
                self._set_global_circuit_state(CircuitState.CLOSED, metadata)
                self._handle_circuit_closed()
                logger.info("Circuit breaker manually closed")
                return True
            else:
                logger.info("Circuit breaker already closed")
                return False
                
        except Exception as e:
            logger.error(f"Error manually closing circuit: {e}")
            return False

    def should_allow_request(self) -> bool:
        """
        Check if requests should be allowed based on global circuit state.
        Simplified: only check global state.
        """
        try:
            state = self.get_global_circuit_state()
            return state == CircuitState.CLOSED
        except Exception as e:
            logger.error(f"Error checking if request allowed: {e}")
            # Fail safe - allow request if we can't determine state
            return True

    def _handle_circuit_opened(self, error: str):
        """Handle circuit breaker opening - pause all jobs."""
        try:
            # Import here to avoid circular imports
            from app.core.queue_manager import get_queue_manager
            
            queue_manager = get_queue_manager()
            queue_manager.pause_all_jobs_on_breaker_open(error)
            
            logger.warning(f"Circuit breaker opened due to: {error}")
            
        except Exception as e:
            logger.error(f"Error handling circuit opened: {e}")

    def _handle_circuit_closed(self):
        """Handle circuit breaker closing - resume all jobs."""
        try:
            # Import here to avoid circular imports
            from app.core.queue_manager import get_queue_manager
            
            queue_manager = get_queue_manager()
            resumed_count = queue_manager.resume_all_jobs_on_breaker_close()
            
            logger.info(f"Circuit breaker closed, resumed {resumed_count} jobs")
            
        except Exception as e:
            logger.error(f"Error handling circuit closed: {e}")

    def get_circuit_status(self) -> Dict[str, Any]:
        """Get comprehensive circuit breaker status."""
        try:
            circuit_data = self.redis.get(self._get_global_circuit_key())
            if not circuit_data:
                return {
                    'state': CircuitState.CLOSED.value,
                    'opened_at': None,
                    'closed_at': None,
                    'metadata': {}
                }
            
            data = json.loads(circuit_data)
            return {
                'state': data.get('state', CircuitState.CLOSED.value),
                'opened_at': data.get('opened_at'),
                'closed_at': data.get('closed_at'),
                'metadata': data.get('metadata', {})
            }
            
        except Exception as e:
            logger.error(f"Error getting circuit status: {e}")
            return {
                'state': CircuitState.CLOSED.value,
                'error': str(e)
            }

    def health_check(self) -> Dict[str, Any]:
        """Health check for circuit breaker."""
        try:
            state = self.get_global_circuit_state()
            return {
                'status': 'healthy',
                'global_circuit_state': state.value,
                'redis_connected': True
            }
        except Exception as e:
            logger.error(f"Circuit breaker health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'redis_connected': False
            }

    # Legacy methods for backward compatibility during transition
    # These will be removed in later phases
    
    def get_circuit_state(self, service: ThirdPartyService) -> CircuitState:
        """Legacy method - returns global state regardless of service."""
        logger.warning(f"Using legacy get_circuit_state for {service}, returning global state")
        return self.get_global_circuit_state()
    
    def should_allow_request_legacy(self, service: ThirdPartyService) -> tuple[bool, str]:
        """Legacy method - returns global state regardless of service."""
        logger.warning(f"Using legacy should_allow_request for {service}, returning global state")
        allowed = self.should_allow_request()
        reason = "global circuit open" if not allowed else "global circuit closed"
        return allowed, reason


def get_circuit_breaker(redis_client: Redis = None) -> CircuitBreakerService:
    """Factory function to get circuit breaker instance."""
    if redis_client is None:
        from app.core.dependencies import get_redis_client
        redis_client = get_redis_client()
    
    return CircuitBreakerService(redis_client) 