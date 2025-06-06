/**
 * Queue Management and Circuit Breaker Type Definitions
 * 
 * These interfaces match the backend schemas defined in:
 * - app/schemas/circuit_breaker.py
 * - API response patterns from queue endpoints
 */

// Circuit breaker state enum matching backend CircuitState
export type CircuitState = 'open' | 'closed';

/**
 * Circuit breaker status information
 * Matches CircuitBreakerStatus from app/schemas/circuit_breaker.py
 */
export interface CircuitBreakerStatus {
  /** Current circuit breaker state */
  state: CircuitState;
  /** ISO timestamp when circuit was opened, null if never opened */
  opened_at: string | null;
  /** ISO timestamp when circuit was closed, null if never closed */
  closed_at: string | null;
  /** Additional circuit breaker metadata (failure reasons, manual actions, etc.) */
  metadata: Record<string, any>;
}

/**
 * Standard API response for circuit breaker status
 * Matches CircuitBreakerStatusResponse from queue.py
 */
export interface CircuitBreakerStatusResponse {
  /** Response status - typically "success" */
  status: string;
  /** Circuit breaker status data */
  data: CircuitBreakerStatus;
}

/**
 * Circuit breaker operation result
 * Matches CircuitBreakerOperation from app/schemas/circuit_breaker.py
 */
export interface CircuitBreakerOperation {
  /** Whether the operation was successful */
  success: boolean;
  /** State before the operation */
  previous_state: CircuitState;
  /** State after the operation */
  current_state: CircuitState;
  /** Human-readable operation result message */
  message: string;
  /** ISO timestamp when operation occurred */
  timestamp: string;
}

/**
 * Standard API response for circuit breaker operations
 */
export interface CircuitBreakerOperationResponse {
  /** Response status - typically "success" */
  status: string;
  /** Operation result data */
  data: CircuitBreakerOperation;
}

/**
 * Extended response for connectivity error handling
 * Used internally by queue service for error state management
 */
export interface ConnectivityErrorResponse {
  status: 'connectivity_error';
  data: null;
  consecutiveErrors: number;
  message: string;
}

/**
 * Queue management comprehensive data structure
 * For future expansion when more queue endpoints are integrated
 */
export interface QueueManagementData {
  /** Circuit breaker status */
  circuit_breaker: CircuitBreakerStatus;
  /** Job counts by status (optional, for future use) */
  job_counts?: Record<string, number>;
  /** Timestamp of data collection */
  timestamp?: string;
}

/**
 * Queue management API response
 */
export interface QueueManagementResponse {
  status: string;
  data: QueueManagementData;
} 