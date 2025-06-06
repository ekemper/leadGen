"""
Queue Management API Endpoints

This module provides circuit breaker API endpoints for manual control
of the global circuit breaker state.
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_active_user
from app.core.circuit_breaker import get_circuit_breaker
from app.models.user import User
from app.schemas.circuit_breaker import (
    CircuitState,
    CircuitBreakerStatus,
    CircuitBreakerOperation
)

# Request models
class CircuitBreakerActionRequest(BaseModel):
    """Request model for circuit breaker operations."""
    reason: Optional[str] = Field(None, description="Optional reason for the operation")

# Response models following established patterns
class CircuitBreakerStatusResponse(BaseModel):
    """Response model for GET circuit breaker status."""
    status: str = Field(..., description="Response status")
    data: CircuitBreakerStatus = Field(..., description="Circuit breaker status information")

class CircuitBreakerOperationResponse(BaseModel):
    """Response model for circuit breaker operations."""
    status: str = Field(..., description="Response status")
    data: CircuitBreakerOperation = Field(..., description="Circuit breaker operation result")

router = APIRouter()

@router.get("/circuit-breaker-status", response_model=CircuitBreakerStatusResponse)
async def get_circuit_breaker_status(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current global circuit breaker status.
    
    Returns comprehensive information about the circuit breaker state,
    including timestamps and metadata.
    """
    try:
        # Get circuit breaker service
        circuit_breaker = get_circuit_breaker()
        
        # Get circuit breaker status
        status_data = circuit_breaker.get_circuit_status()
        
        # Create response model
        circuit_status = CircuitBreakerStatus(
            state=CircuitState(status_data["state"]),
            opened_at=status_data.get("opened_at"),
            closed_at=status_data.get("closed_at"),
            metadata=status_data.get("metadata", {})
        )
        
        return CircuitBreakerStatusResponse(
            status="success",
            data=circuit_status
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving circuit breaker status: {str(e)}"
        )

@router.post("/close-circuit-breaker", response_model=CircuitBreakerOperationResponse)
async def close_circuit_breaker(
    request: CircuitBreakerActionRequest = CircuitBreakerActionRequest(),
    current_user: User = Depends(get_current_active_user)
):
    """
    Manually close the circuit breaker.
    
    This will resume all paused jobs and allow normal operation.
    The circuit breaker will remain closed until a failure occurs
    or it is manually opened.
    """
    try:
        # Get circuit breaker service
        circuit_breaker = get_circuit_breaker()
        
        # Get current state before operation
        current_state = circuit_breaker.get_global_circuit_state()
        
        # Attempt to close circuit
        success = circuit_breaker.manually_close_circuit()
        
        # Get new state after operation
        new_state = circuit_breaker.get_global_circuit_state()
        
        # Create operation result
        if success:
            message = f"Circuit breaker successfully closed. {request.reason or 'No reason provided'}"
        else:
            message = "Circuit breaker was already closed"
            
        operation_result = CircuitBreakerOperation(
            success=success,
            previous_state=current_state,
            current_state=new_state,
            message=message,
            timestamp=datetime.utcnow().isoformat()
        )
        
        return CircuitBreakerOperationResponse(
            status="success",
            data=operation_result
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error closing circuit breaker: {str(e)}"
        )

@router.post("/open-circuit-breaker", response_model=CircuitBreakerOperationResponse)
async def open_circuit_breaker(
    request: CircuitBreakerActionRequest = CircuitBreakerActionRequest(),
    current_user: User = Depends(get_current_active_user)
):
    """
    Manually open the circuit breaker.
    
    This will immediately pause all running jobs and block new operations.
    The circuit breaker will remain open until manually closed.
    """
    try:
        # Get circuit breaker service
        circuit_breaker = get_circuit_breaker()
        
        # Get current state before operation
        current_state = circuit_breaker.get_global_circuit_state()
        
        # Prepare reason for opening
        reason = request.reason or "Manual API call"
        
        # Attempt to open circuit
        success = circuit_breaker.manually_open_circuit(reason)
        
        # Get new state after operation
        new_state = circuit_breaker.get_global_circuit_state()
        
        # Create operation result
        if success:
            message = f"Circuit breaker successfully opened. Reason: {reason}"
        else:
            message = "Circuit breaker was already open"
            
        operation_result = CircuitBreakerOperation(
            success=success,
            previous_state=current_state,
            current_state=new_state,
            message=message,
            timestamp=datetime.utcnow().isoformat()
        )
        
        return CircuitBreakerOperationResponse(
            status="success",
            data=operation_result
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error opening circuit breaker: {str(e)}"
        )