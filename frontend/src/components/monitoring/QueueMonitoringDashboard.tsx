import React, { useState, useEffect, useCallback } from 'react';
import queueService from '../../services/queueService';
import { 
  CircuitBreakerStatus, 
  CircuitBreakerStatusResponse, 
  ConnectivityErrorResponse 
} from '../../types/queue';

/**
 * Interface for the queue monitoring component state
 */
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

/**
 * QueueMonitoringDashboard Component
 * 
 * Provides real-time monitoring of circuit breaker status with:
 * - 2-second polling for status updates
 * - Connectivity loss detection after 5 consecutive errors
 * - Manual circuit breaker toggle controls
 * - Automatic cleanup on component unmount
 */
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

  /**
   * Handle circuit breaker status updates from polling
   * Manages both successful responses and connectivity errors
   */
  const handleCircuitBreakerUpdate = useCallback((response: CircuitBreakerStatusResponse | ConnectivityErrorResponse) => {
    if (response.status === 'connectivity_error') {
      const connectivityError = response as ConnectivityErrorResponse;
      setState(prev => ({
        ...prev,
        connectivityLost: true,
        consecutiveErrors: connectivityError.consecutiveErrors,
        error: connectivityError.message,
        isLoading: false
      }));
    } else {
      const statusResponse = response as CircuitBreakerStatusResponse;
      setState(prev => ({
        ...prev,
        circuitBreakerStatus: statusResponse.data,
        isLoading: false,
        error: null,
        lastUpdated: new Date(),
        connectivityLost: false,
        consecutiveErrors: 0
      }));
    }
  }, []);

  /**
   * Handle manual circuit breaker toggle operations
   * Prevents double-clicks and provides user feedback
   */
  const handleToggleCircuitBreaker = useCallback(async () => {
    if (!state.circuitBreakerStatus || state.isTogglingBreaker) return;

    setState(prev => ({ ...prev, isTogglingBreaker: true }));

    try {
      const currentState = state.circuitBreakerStatus.state;
      const reason = `Manual toggle from dashboard - ${currentState === 'open' ? 'closing' : 'opening'} circuit breaker`;

      await queueService.toggleCircuitBreaker(currentState, reason);

      // Status will be updated via polling - no need to manually update state
    } catch (error) {
      console.error('Failed to toggle circuit breaker:', error);
      setState(prev => ({ 
        ...prev, 
        error: `Failed to ${state.circuitBreakerStatus?.state === 'open' ? 'close' : 'open'} circuit breaker: ${error}`
      }));
    } finally {
      setState(prev => ({ ...prev, isTogglingBreaker: false }));
    }
  }, [state.circuitBreakerStatus, state.isTogglingBreaker]);

  /**
   * Start polling on component mount and cleanup on unmount
   */
  useEffect(() => {
    const pollingId = queueService.startCircuitBreakerPolling(
      handleCircuitBreakerUpdate,
      2000 // 2 second interval as specified
    );

    setState(prev => ({ ...prev, pollingId }));

    // Cleanup function to stop polling when component unmounts
    return () => {
      if (pollingId) {
        queueService.stopPolling(pollingId);
      }
    };
  }, [handleCircuitBreakerUpdate]);

  // Render loading state
  if (state.isLoading && !state.circuitBreakerStatus) {
    return (
      <div className="queue-monitoring-dashboard p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-gray-600 dark:text-gray-400">Loading queue status...</p>
          </div>
        </div>
      </div>
    );
  }

  // Render connectivity lost state
  if (state.connectivityLost) {
    return (
      <div className="queue-monitoring-dashboard p-6">
        <div className="max-w-2xl mx-auto">
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
            <div className="flex items-center mb-4">
              <div className="flex-shrink-0">
                <svg className="h-8 w-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-lg font-semibold text-red-800 dark:text-red-200">
                  ⚠️ Connection Lost
                </h3>
              </div>
            </div>
            
            <div className="text-red-700 dark:text-red-300 mb-4">
              <p className="mb-2">{state.error}</p>
              <p className="text-sm">Consecutive errors: {state.consecutiveErrors}</p>
            </div>
            
            <button 
              onClick={() => window.location.reload()}
              className="bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200"
            >
              Refresh Page
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Render error state (non-connectivity errors)
  if (state.error && !state.connectivityLost) {
    return (
      <div className="queue-monitoring-dashboard p-6">
        <div className="max-w-2xl mx-auto">
          <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-yellow-800 dark:text-yellow-200">Error: {state.error}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Main dashboard render
  return (
    <div className="queue-monitoring-dashboard p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Queue Monitoring Dashboard
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Real-time monitoring of circuit breaker status and queue health
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Circuit Breaker Status Indicator */}
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
        </div>

        {/* Additional monitoring components can be added here in the future */}
        <div className="mt-6 text-center text-sm text-gray-500 dark:text-gray-400">
          Last updated: {state.lastUpdated ? state.lastUpdated.toLocaleString() : 'Never'} • 
          Polling every 2 seconds
        </div>
      </div>
    </div>
  );
};

/**
 * Circuit Breaker Status Indicator Component
 * Displays current status with visual indicators and metadata
 */
interface CircuitBreakerStatusIndicatorProps {
  status: CircuitBreakerStatus | null;
  lastUpdated: Date | null;
}

const CircuitBreakerStatusIndicator: React.FC<CircuitBreakerStatusIndicatorProps> = ({ 
  status, 
  lastUpdated 
}) => {
  if (!status) {
    return (
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Circuit Breaker Status
        </h2>
        <p className="text-gray-500 dark:text-gray-400">No status data available</p>
      </div>
    );
  }

  const isOpen = status.state === 'open';
  const statusColor = isOpen ? 'red' : 'green';
  const statusIcon = isOpen ? '🔴' : '🟢';

  return (
    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
        Circuit Breaker Status
      </h2>
      
      <div className="flex items-center mb-4">
        <span className="text-2xl mr-3">{statusIcon}</span>
        <div>
          <p className={`text-lg font-bold ${isOpen ? 'text-red-600' : 'text-green-600'}`}>
            {status.state.toUpperCase()}
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {isOpen ? 'System is blocked' : 'System is operational'}
          </p>
        </div>
      </div>

      {/* Timestamps */}
      <div className="space-y-2 text-sm">
        {status.opened_at && (
          <div>
            <span className="font-medium text-gray-700 dark:text-gray-300">Last Opened:</span>
            <span className="ml-2 text-gray-600 dark:text-gray-400">
              {new Date(status.opened_at).toLocaleString()}
            </span>
          </div>
        )}
        {status.closed_at && (
          <div>
            <span className="font-medium text-gray-700 dark:text-gray-300">Last Closed:</span>
            <span className="ml-2 text-gray-600 dark:text-gray-400">
              {new Date(status.closed_at).toLocaleString()}
            </span>
          </div>
        )}
      </div>

      {/* Metadata */}
      {Object.keys(status.metadata).length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <h4 className="font-medium text-gray-900 dark:text-white mb-2">Additional Info:</h4>
          <div className="space-y-1 text-sm">
            {Object.entries(status.metadata).map(([key, value]) => (
              <div key={key}>
                <span className="font-medium text-gray-700 dark:text-gray-300">
                  {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:
                </span>
                <span className="ml-2 text-gray-600 dark:text-gray-400">
                  {typeof value === 'string' ? value : JSON.stringify(value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

/**
 * Circuit Breaker Toggle Controls Component
 * Provides manual control over circuit breaker state
 */
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
  if (!status) {
    return (
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Manual Controls
        </h2>
        <p className="text-gray-500 dark:text-gray-400">Controls unavailable - no status data</p>
      </div>
    );
  }

  const isOpen = status.state === 'open';
  const buttonText = isToggling 
    ? (isOpen ? 'Closing...' : 'Opening...') 
    : (isOpen ? 'Close Circuit Breaker' : 'Open Circuit Breaker');
  
  const buttonColorClass = isOpen 
    ? 'bg-green-600 hover:bg-green-700 focus:ring-green-500' 
    : 'bg-red-600 hover:bg-red-700 focus:ring-red-500';

  return (
    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
        Manual Circuit Breaker Controls
      </h2>
      
      <div className="space-y-4">
        <div>
          <p className="text-gray-700 dark:text-gray-300 mb-2">
            Current State: <strong className={isOpen ? 'text-red-600' : 'text-green-600'}>
              {status.state.toUpperCase()}
            </strong>
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            {isOpen 
              ? 'Click below to restore normal operations' 
              : 'Click below to manually block operations'
            }
          </p>
        </div>
        
        <button 
          className={`w-full ${buttonColorClass} text-white font-medium py-3 px-4 rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed`}
          onClick={onToggle}
          disabled={isToggling}
        >
          {buttonText}
        </button>
        
        {isToggling && (
          <p className="text-sm text-gray-500 dark:text-gray-400 text-center">
            ⏳ Operation in progress... Status will update automatically.
          </p>
        )}
      </div>
    </div>
  );
};

export default QueueMonitoringDashboard; 