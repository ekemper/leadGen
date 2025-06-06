"""
Circuit Breaker Schemas

This module defines Pydantic models for circuit breaker API responses.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class CircuitState(str, Enum):
    """Circuit breaker state enumeration."""
    CLOSED = "closed"    # Normal operation
    OPEN = "open"       # Failing, requests blocked


class CircuitBreakerStatus(BaseModel):
    """Schema for circuit breaker status information."""
    state: CircuitState = Field(..., description="Current circuit breaker state")
    opened_at: Optional[str] = Field(None, description="ISO timestamp when circuit was opened")
    closed_at: Optional[str] = Field(None, description="ISO timestamp when circuit was closed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional circuit breaker metadata")

    class Config:
        from_attributes = True


class CircuitBreakerOperation(BaseModel):
    """Schema for circuit breaker operation result."""
    success: bool = Field(..., description="Whether the operation was successful")
    previous_state: CircuitState = Field(..., description="State before the operation")
    current_state: CircuitState = Field(..., description="State after the operation")
    message: str = Field(..., description="Human-readable operation result message")
    timestamp: str = Field(..., description="ISO timestamp when operation occurred")

    class Config:
        from_attributes = True 