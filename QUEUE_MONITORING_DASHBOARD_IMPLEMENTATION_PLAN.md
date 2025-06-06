# Queue Monitoring Dashboard Implementation Plan

## Overview

This document provides an extremely detailed step-by-step implementation plan for integrating the `get_circuit_breaker_status` endpoint with the `QueueMonitoringDashboard` component and creating a comprehensive queue management service for the frontend.

## General Rules and Instructions

### Critical Assessment Requirement
- **ALWAYS** make a technical, critical assessment for any queries, statements, ideas, questions
- Don't be afraid to question the user's plan or implementation approach
- NEVER MAKE SHIT UP - always provide rationale for decisions

### Code Quality Standards  
- Always check for consistency in function signatures compared to their usage - for EVERY change
- Maintain current patterns, conventions, and configuration for this app at all costs
- Use copious doc strings and comments in source code to add context for decisions
- If there are significant changes, create markdown documentation in the documentation directory

### Implementation Standards
- Always ask for more clarification from the user when implementing steps of the plan
- In cases where there are code edits, the AI agent is to perform the changes
- In cases where there are commands to be run, run them in the chat window context and parse output for errors
- Never use deprecated `docker-compose` command - always use `docker compose`
- For commands needing database/redis connection, run them in the API container

### Environment and Configuration
- To assess environment variables: run `cat .env`
- DO NOT create, modify, or otherwise interfere with env files
- For configuration changes, ask the user to add or change values
- Before creating commands with container names, run `docker ps` to get correct names

## Current Architecture Assessment

### Backend Architecture
- **Framework**: FastAPI with Python
- **API Version**: v1 (prefix: `/api/v1`)
- **Circuit Breaker Endpoint**: `GET /api/v1/queue/circuit-breaker-status`
- **Authentication**: Bearer token authentication via Authorization header
- **Response Format**: Standardized with `status` and `data` fields

### Frontend Architecture
- **Framework**: React with TypeScript
- **State Management**: React hooks (useState, useEffect)
- **API Layer**: Centralized `api` utility in `frontend/src/config/api.ts`
- **Service Pattern**: Service classes for API logic (campaignService, jobService, etc.)
- **Component Structure**: Feature-based organization under `frontend/src/components/`

### Current QueueMonitoringDashboard State
- **Location**: `frontend/src/components/monitoring/QueueMonitoringDashboard.tsx`
- **Current Implementation**: Minimal placeholder returning `<div>Queue Monitoring Dashboard</div>`
- **Integration**: Already routed at `/queue-monitoring` path

## Implementation Plan

### Phase 1: Backend Endpoint Verification and Analysis

#### Step 1.1: Verify Circuit Breaker Endpoint Functionality
**Goal**: Confirm the existing endpoint works correctly and understand its response structure.

**Actions**:
1. Run the API in development mode
2. Test the circuit breaker endpoint manually
3. Document the exact response format

**Commands to Execute**:
```bash
# Check if containers are running
docker ps

# Start API if not running
docker compose up -d api

# Get auth token for testing
# (Implementation note: This will require user to provide test credentials)

# Test the endpoint directly
curl -X GET "http://localhost:8000/api/v1/queue/circuit-breaker-status" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json"
```

**Success Criteria**:
- Endpoint returns 200 status code
- Response follows the pattern: `{"status": "success", "data": {...}}`
- `data` object contains circuit breaker information with state, timestamps, and metadata

#### Step 1.2: Analyze Response Schema Compliance
**Goal**: Ensure backend response matches expected frontend TypeScript interfaces.

**Actions**:
1. Review `app/schemas/circuit_breaker.py` for backend schema
2. Check if frontend types exist for circuit breaker data
3. Identify any schema mismatches

**Files to Review**:
- `app/schemas/circuit_breaker.py`
- `frontend/src/types/` (search for circuit breaker or queue types)

**Success Criteria**:
- Backend schema is well-defined and matches API endpoint response
- Identify if frontend TypeScript interfaces need to be created

### Phase 2: Frontend TypeScript Types and Interfaces

#### Step 2.1: Create Circuit Breaker TypeScript Interfaces
**Goal**: Define proper TypeScript interfaces for circuit breaker data.

**Actions**:
1. Create or update `frontend/src/types/queue.ts`
2. Define interfaces matching backend schema
3. Export interfaces for use in components and services

**Files to Create/Modify**:
- `frontend/src/types/queue.ts`

**Interface Structure** (based on backend schema):
```typescript
export interface CircuitBreakerStatus {
  state: 'open' | 'closed';
  opened_at: string | null;
  closed_at: string | null;
  metadata: Record<string, any>;
}

export interface CircuitBreakerStatusResponse {
  status: string;
  data: CircuitBreakerStatus;
}

export interface QueueManagementData {
  circuit_breaker: CircuitBreakerStatus;
  job_counts?: Record<string, number>;
  timestamp?: string;
}
```

**Success Criteria**:
- TypeScript interfaces accurately reflect backend schema
- Interfaces are properly exported and documented
- No TypeScript compilation errors

#### Step 2.2: Update Service Index Exports
**Goal**: Ensure new queue service will be properly exported.

**Actions**:
1. Prepare `frontend/src/services/index.ts` for queue service export
2. Document the export pattern for consistency

**Files to Modify**:
- `frontend/src/services/index.ts`

**Success Criteria**:
- Export structure is prepared for queue service addition
- Follows existing service export patterns

### Phase 3: Queue Management Service Creation

#### Step 3.1: Create Queue Management Service Class
**Goal**: Create a comprehensive service class for all queue-related API operations.

**Actions**:
1. Create `frontend/src/services/queueService.ts`
2. Implement circuit breaker status fetching
3. Add error handling and authentication
4. Follow established service patterns from other services

**Files to Create**:
- `frontend/src/services/queueService.ts`

**Service Implementation Structure**:
```typescript
import { api } from '../config/api';
import { CircuitBreakerStatusResponse, QueueManagementData } from '../types/queue';

class QueueService {
  /**
   * Get current circuit breaker status
   * Polls the circuit breaker endpoint for real-time status
   */
  async getCircuitBreakerStatus(): Promise<CircuitBreakerStatusResponse> {
    return await api.get('/queue/circuit-breaker-status');
  }

  private pollingIntervals: Map<string, NodeJS.Timeout> = new Map();

  /**
   * Start polling circuit breaker status
   * @param callback Function to call with status updates
   * @param intervalMs Polling interval in milliseconds (default: 2000)
   * @returns Polling ID for cleanup
   */
  startCircuitBreakerPolling(
    callback: (status: CircuitBreakerStatusResponse) => void,
    intervalMs: number = 2000
  ): string {
    const pollingId = `circuit-breaker-${Date.now()}`;
    let consecutiveErrors = 0;
    
    const poll = async () => {
      try {
        const status = await this.getCircuitBreakerStatus();
        callback(status);
        consecutiveErrors = 0; // Reset error count on success
      } catch (error) {
        console.error('Circuit breaker polling error:', error);
        consecutiveErrors++;
        
        // If 5 consecutive errors, stop polling and notify connectivity loss
        if (consecutiveErrors >= 5) {
          console.warn('Circuit breaker polling stopped due to connectivity issues');
          this.stopPolling(pollingId);
          callback({
            status: 'connectivity_error',
            data: null,
            consecutiveErrors,
            message: 'Connection lost. Please refresh the page to resume monitoring.'
          } as any); // Type assertion for error state
          return;
        }
      }
    };

    // Initial poll
    poll();
    
    // Set up interval
    const interval = setInterval(poll, intervalMs);
    this.pollingIntervals.set(pollingId, interval);
    
    return pollingId;
  }

  /**
   * Manually open the circuit breaker
   * @param reason Optional reason for opening the circuit breaker
   */
  async openCircuitBreaker(reason?: string): Promise<any> {
    return await api.post('/queue/open-circuit-breaker', { reason });
  }

  /**
   * Manually close the circuit breaker
   * @param reason Optional reason for closing the circuit breaker
   */
  async closeCircuitBreaker(reason?: string): Promise<any> {
    return await api.post('/queue/close-circuit-breaker', { reason });
  }

  /**
   * Stop polling for a specific polling ID
   */
  stopPolling(pollingId: string): void {
    const interval = this.pollingIntervals.get(pollingId);
    if (interval) {
      clearInterval(interval);
      this.pollingIntervals.delete(pollingId);
    }
  }

  /**
   * Stop all polling operations
   */
  stopAllPolling(): void {
    this.pollingIntervals.forEach((interval) => clearInterval(interval));
    this.pollingIntervals.clear();
  }
}

export default new QueueService();
```

**Success Criteria**:
- Service class follows established patterns from `campaignService.ts` and `jobService.ts`
- Proper error handling implemented
- Authentication headers automatically included via `api` utility
- Methods return properly typed responses
- **5-consecutive-error detection** stops polling and shows connectivity loss
- **Manual circuit breaker controls** are available via service methods
- Memory leaks are prevented through proper cleanup

### Phase 4: QueueMonitoringDashboard Component Development

#### Step 4.1: Design Component State Management
**Goal**: Plan the component's state structure and update patterns.

**Actions**:
1. Define component state interface
2. Plan state update flow
3. Design error handling strategy

**State Structure**:
```typescript
interface QueueMonitoringState {
  circuitBreakerStatus: CircuitBreakerStatus | null;
  isLoading: boolean;
  error: string | null;
  lastUpdated: Date | null;
  pollingId: string | null;
  connectivityLost: boolean;         // New: Track connectivity issues
  consecutiveErrors: number;         // New: Track error count
  isTogglingBreaker: boolean;       // New: Track manual toggle operations
}
```

**Success Criteria**:
- State structure supports all required UI elements
- Loading states are properly managed
- Error conditions are handled gracefully
- **Connectivity loss state** is tracked and displayed
- **Manual toggle state** prevents double-operations

#### Step 4.2: Implement Core Component Logic
**Goal**: Build the main component with polling integration.

**Actions**:
1. Replace placeholder QueueMonitoringDashboard with full implementation
2. Integrate queue service
3. Implement lifecycle management for polling
4. **Add connectivity loss handling**
5. **Add manual circuit breaker toggle**

**Files to Modify**:
- `frontend/src/components/monitoring/QueueMonitoringDashboard.tsx`

**Component Implementation Structure**:
```typescript
import React, { useState, useEffect, useCallback } from 'react';
import queueService from '../../services/queueService';
import { CircuitBreakerStatus } from '../../types/queue';

interface QueueMonitoringState {
  circuitBreakerStatus: CircuitBreakerStatus | null;
  isLoading: boolean;
  error: string | null;
  lastUpdated: Date | null;
  pollingId: string | null;
  connectivityLost: boolean;
  consecutiveErrors: number;
  isTogglingBreaker: boolean;
}

const QueueMonitoringDashboard: React.FC = () => {
  const [state, setState] = useState<QueueMonitoringState>({
    circuitBreakerStatus: null,
    isLoading: true,
    error: null,
    lastUpdated: null,
    pollingId: null,
    connectivityLost: false,
    consecutiveErrors: 0,
    isTogglingBreaker: false
  });

  // Circuit breaker status update handler
  const handleCircuitBreakerUpdate = useCallback((response: any) => {
    if (response.status === 'connectivity_error') {
      setState(prev => ({
        ...prev,
        connectivityLost: true,
        consecutiveErrors: response.consecutiveErrors,
        error: response.message,
        isLoading: false
      }));
    } else {
      setState(prev => ({
        ...prev,
        circuitBreakerStatus: response.data,
        isLoading: false,
        error: null,
        lastUpdated: new Date(),
        connectivityLost: false,
        consecutiveErrors: 0
      }));
    }
  }, []);

  // Manual circuit breaker toggle handler
  const handleToggleCircuitBreaker = useCallback(async () => {
    if (!state.circuitBreakerStatus || state.isTogglingBreaker) return;

    setState(prev => ({ ...prev, isTogglingBreaker: true }));

    try {
      const currentState = state.circuitBreakerStatus.state;
      const reason = `Manual toggle from dashboard - ${currentState === 'open' ? 'closing' : 'opening'} circuit breaker`;

      if (currentState === 'open') {
        await queueService.closeCircuitBreaker(reason);
      } else {
        await queueService.openCircuitBreaker(reason);
      }

      // Status will be updated via polling
    } catch (error) {
      console.error('Failed to toggle circuit breaker:', error);
      setState(prev => ({ 
        ...prev, 
        error: `Failed to ${state.circuitBreakerStatus?.state === 'open' ? 'close' : 'open'} circuit breaker`
      }));
    } finally {
      setState(prev => ({ ...prev, isTogglingBreaker: false }));
    }
  }, [state.circuitBreakerStatus, state.isTogglingBreaker]);

  // Start polling on component mount
  useEffect(() => {
    const pollingId = queueService.startCircuitBreakerPolling(
      handleCircuitBreakerUpdate,
      2000 // 2 second interval as requested
    );

    setState(prev => ({ ...prev, pollingId }));

    // Cleanup on unmount
    return () => {
      if (pollingId) {
        queueService.stopPolling(pollingId);
      }
    };
  }, [handleCircuitBreakerUpdate]);

  // Error boundary and loading states
  if (state.isLoading && !state.circuitBreakerStatus) {
    return <div>Loading queue status...</div>;
  }

  if (state.connectivityLost) {
    return (
      <div className="queue-monitoring-dashboard">
        <div className="connectivity-error">
          <h3>⚠️ Connection Lost</h3>
          <p>{state.error}</p>
          <p>Consecutive errors: {state.consecutiveErrors}</p>
          <button onClick={() => window.location.reload()}>
            Refresh Page
          </button>
        </div>
      </div>
    );
  }

  if (state.error && !state.connectivityLost) {
    return <div>Error: {state.error}</div>;
  }

  return (
    <div className="queue-monitoring-dashboard">
      {/* Status indicator implementation */}
      <CircuitBreakerStatusIndicator 
        status={state.circuitBreakerStatus} 
        lastUpdated={state.lastUpdated}
      />
      
      {/* Manual Circuit Breaker Controls */}
      <CircuitBreakerToggleControls
        status={state.circuitBreakerStatus}
        isToggling={state.isTogglingBreaker}
        onToggle={handleToggleCircuitBreaker}
      />
      
      {/* Additional queue monitoring components */}
    </div>
  );
};

export default QueueMonitoringDashboard;
```

**Success Criteria**:
- Component polls circuit breaker status every 2 seconds
- UI updates reflect current circuit breaker state
- Component properly cleans up polling on unmount
- Error states are handled gracefully
- **Connectivity loss** is detected and displayed with refresh option
- **Manual toggle controls** allow opening/closing circuit breaker
- **Toggle operations** are tracked to prevent double-clicks

#### Step 4.3: Create Status Indicator Sub-Component
**Goal**: Create a reusable status indicator component for circuit breaker state.

**Actions**:
1. Create `CircuitBreakerStatusIndicator` component
2. Implement visual status representation
3. Add status metadata display

**Files to Create**:
- `frontend/src/components/monitoring/CircuitBreakerStatusIndicator.tsx`

**Component Features**:
- Visual indicator (red/green) for open/closed states
- Timestamp display for state changes
- Metadata display for failure reasons
- Responsive design following app's design system

**Success Criteria**:
- Clear visual distinction between open and closed states
- Displays relevant metadata and timestamps
- Follows existing component patterns and styling
- Accessible and responsive design

#### Step 4.4: Create Manual Circuit Breaker Toggle Controls
**Goal**: Create controls for manual circuit breaker operations.

**Actions**:
1. Create `CircuitBreakerToggleControls` component
2. Implement toggle button with proper states
3. Add confirmation and feedback mechanisms

**Files to Create**:
- `frontend/src/components/monitoring/CircuitBreakerToggleControls.tsx`

**Component Features**:
- Toggle button that shows current state and next action
- Loading state during toggle operations
- Clear visual feedback for state changes
- Confirmation for critical operations (optional enhancement)

**Component Implementation Structure**:
```typescript
import React from 'react';
import { CircuitBreakerStatus } from '../../types/queue';

interface CircuitBreakerToggleControlsProps {
  status: CircuitBreakerStatus | null;
  isToggling: boolean;
  onToggle: () => void;
}

const CircuitBreakerToggleControls: React.FC<CircuitBreakerToggleControlsProps> = ({
  status,
  isToggling,
  onToggle
}) => {
  if (!status) return null;

  const isOpen = status.state === 'open';
  const buttonText = isToggling 
    ? (isOpen ? 'Closing...' : 'Opening...') 
    : (isOpen ? 'Close Circuit Breaker' : 'Open Circuit Breaker');
  
  const buttonClass = `circuit-breaker-toggle ${isOpen ? 'close-action' : 'open-action'} ${isToggling ? 'loading' : ''}`;

  return (
    <div className="circuit-breaker-controls">
      <h3>Manual Circuit Breaker Controls</h3>
      <div className="control-section">
        <p>Current State: <strong>{status.state.toUpperCase()}</strong></p>
        <button 
          className={buttonClass}
          onClick={onToggle}
          disabled={isToggling}
        >
          {buttonText}
        </button>
        {isToggling && (
          <p className="operation-note">
            Operation in progress... Status will update automatically.
          </p>
        )}
      </div>
    </div>
  );
};

export default CircuitBreakerToggleControls;
```

**Success Criteria**:
- Toggle controls clearly show current state and available actions
- Loading states prevent double-operations
- Visual feedback is immediate and clear
- Component integrates seamlessly with dashboard layout
- Follows app's existing button and control patterns

### Phase 5: Integration Testing and Validation

#### Step 5.1: Component Integration Testing
**Goal**: Verify the component works correctly in the application context.

**Actions**:
1. Test component mounting and unmounting
2. Verify polling starts and stops correctly
3. Test error scenarios (network failures, invalid responses)
4. Validate memory leak prevention

**Testing Commands**:
```bash
# Start the frontend development server
cd frontend
npm run dev

# Navigate to queue monitoring page and observe:
# - Initial loading state
# - Polling behavior (network tab in browser dev tools)
# - Status updates every 2 seconds
# - Component cleanup when navigating away
```

**Success Criteria**:
- Component loads without errors
- Polling requests visible in network tab every 2 seconds
- Status indicator updates when circuit breaker state changes
- No memory leaks or continued polling after navigation

#### Step 5.2: End-to-End Functionality Testing
**Goal**: Test complete integration from backend to frontend.

**Actions**:
1. Manually trigger circuit breaker state changes via backend API
2. Observe frontend updates in real-time
3. Test edge cases (long polling, network interruptions)

**Testing Sequence**:
```bash
# Terminal 1: Monitor frontend behavior
# Browse to http://localhost:5173/queue-monitoring

# Terminal 2: Change circuit breaker state
# Open circuit breaker
curl -X POST "http://localhost:8000/api/v1/queue/open-circuit-breaker" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Test from implementation plan"}'

# Observe frontend status change to "open"

# Close circuit breaker  
curl -X POST "http://localhost:8000/api/v1/queue/close-circuit-breaker" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Test completion"}'

# Observe frontend status change to "closed"
```

**Success Criteria**:
- Frontend reflects backend state changes within 2-4 seconds
- Status indicator shows correct visual state
- Timestamps and metadata update appropriately
- No console errors during state transitions



## Risk Assessment and Mitigation

### Technical Risks
1. **Polling Performance Impact**
   - **Risk**: Continuous polling may impact performance
   - **Mitigation**: Implement exponential backoff on errors, allow configurable polling intervals

2. **Memory Leaks**
   - **Risk**: Improper cleanup of polling intervals
   - **Mitigation**: Comprehensive useEffect cleanup, polling ID management

3. **Authentication Token Expiry**
   - **Risk**: Long-running polling sessions may encounter expired tokens
   - **Mitigation**: Leverage existing auth error handling in `api` utility

4. **Network Reliability**
   - **Risk**: Network interruptions breaking polling
   - **Mitigation**: Error handling with automatic retry logic

### Business Logic Risks
1. **Circuit Breaker State Inconsistency**
   - **Risk**: Frontend state may lag behind backend changes
   - **Mitigation**: 2-second polling interval should be sufficient for most use cases

2. **User Experience During Failures**
   - **Risk**: Poor UX during network or backend failures
   - **Mitigation**: Clear error messages, graceful degradation

## Conclusion

This implementation plan provides a comprehensive approach to integrating circuit breaker status monitoring into the frontend application. The plan maintains consistency with existing patterns while introducing robust polling and state management capabilities.

The implementation follows the established service pattern, maintains proper TypeScript typing, and ensures clean component lifecycle management. The 2-second polling interval provides near real-time status updates while remaining performant.

All steps include verification criteria and testing procedures to ensure proper functionality and integration with the existing application architecture. 