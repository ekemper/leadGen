import { api } from '../config/api';
import { 
  CircuitBreakerStatusResponse, 
  CircuitBreakerOperationResponse,
  ConnectivityErrorResponse 
} from '../types/queue';

/**
 * Queue Management Service
 * 
 * Provides comprehensive queue and circuit breaker management functionality:
 * - Circuit breaker status polling with error handling
 * - Manual circuit breaker controls (open/close)
 * - Connectivity loss detection and recovery
 * - Memory leak prevention through proper cleanup
 */
class QueueService {
  private pollingIntervals: Map<string, NodeJS.Timeout> = new Map();

  /**
   * Get current circuit breaker status
   * Polls the circuit breaker endpoint for real-time status
   */
  async getCircuitBreakerStatus(): Promise<CircuitBreakerStatusResponse> {
    return await api.get('/queue/circuit-breaker-status');
  }

  /**
   * Start polling circuit breaker status with enhanced error handling
   * @param callback Function to call with status updates or connectivity errors
   * @param intervalMs Polling interval in milliseconds (default: 2000)
   * @returns Polling ID for cleanup
   */
  startCircuitBreakerPolling(
    callback: (status: CircuitBreakerStatusResponse | ConnectivityErrorResponse) => void,
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
          
          const connectivityError: ConnectivityErrorResponse = {
            status: 'connectivity_error',
            data: null,
            consecutiveErrors,
            message: 'Connection lost. Please refresh the page to resume monitoring.'
          };
          
          callback(connectivityError);
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
   * Stop polling for a specific polling ID
   * @param pollingId The polling ID returned from startCircuitBreakerPolling
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
   * Useful for cleanup when multiple polls are running
   */
  stopAllPolling(): void {
    this.pollingIntervals.forEach((interval) => clearInterval(interval));
    this.pollingIntervals.clear();
  }

  /**
   * Manually open the circuit breaker
   * @param reason Optional reason for opening the circuit breaker
   * @returns Promise resolving to operation result
   */
  async openCircuitBreaker(reason?: string): Promise<CircuitBreakerOperationResponse> {
    return await api.post('/queue/open-circuit-breaker', { reason });
  }

  /**
   * Manually close the circuit breaker
   * @param reason Optional reason for closing the circuit breaker
   * @returns Promise resolving to operation result
   */
  async closeCircuitBreaker(reason?: string): Promise<CircuitBreakerOperationResponse> {
    return await api.post('/queue/close-circuit-breaker', { reason });
  }

  /**
   * Toggle circuit breaker state (open -> close, close -> open)
   * @param currentState Current circuit breaker state
   * @param reason Optional reason for the toggle operation
   * @returns Promise resolving to operation result
   */
  async toggleCircuitBreaker(
    currentState: 'open' | 'closed', 
    reason?: string
  ): Promise<CircuitBreakerOperationResponse> {
    const defaultReason = `Manual toggle from dashboard - ${currentState === 'open' ? 'closing' : 'opening'} circuit breaker`;
    const operationReason = reason || defaultReason;

    if (currentState === 'open') {
      return await this.closeCircuitBreaker(operationReason);
    } else {
      return await this.openCircuitBreaker(operationReason);
    }
  }

  /**
   * Get service health information
   * @returns Number of active polling operations
   */
  getServiceHealth(): { activePolls: number; pollingIds: string[] } {
    return {
      activePolls: this.pollingIntervals.size,
      pollingIds: Array.from(this.pollingIntervals.keys())
    };
  }
}

// Export singleton instance
export default new QueueService(); 