import { useState, useCallback } from 'react';
import { useError } from '../context/ErrorContext';
import { useNetwork } from '../context/NetworkContext';

interface RetryOptions {
  maxRetries?: number;
  initialDelay?: number;
  backoffMultiplier?: number;
  maxDelay?: number;
  retryCondition?: (error: any) => boolean;
  onRetry?: (attempt: number, error: any) => void;
  onMaxRetriesReached?: (error: any) => void;
}

interface RetryState {
  isRetrying: boolean;
  retryCount: number;
  lastError: any;
}

export const useRetry = <T extends (...args: any[]) => Promise<any>>(
  operation: T,
  options: RetryOptions = {}
) => {
  const {
    maxRetries = 3,
    initialDelay = 1000,
    backoffMultiplier = 2,
    maxDelay = 10000,
    retryCondition = (error) => {
      // Retry on network errors, 5xx errors, or timeout errors
      return (
        !error.response ||
        error.response.status >= 500 ||
        error.code === 'NETWORK_ERROR' ||
        error.code === 'TIMEOUT'
      );
    },
    onRetry,
    onMaxRetriesReached,
  } = options;

  const [state, setState] = useState<RetryState>({
    isRetrying: false,
    retryCount: 0,
    lastError: null,
  });

  const { handleApiError } = useError();
  const { isOnline, executeWhenOnline } = useNetwork();

  const executeWithRetry = useCallback(
    async (...args: Parameters<T>): Promise<Awaited<ReturnType<T>>> => {
      let attempt = 0;
      let delay = initialDelay;

      const attemptOperation = async (): Promise<Awaited<ReturnType<T>>> => {
        try {
          setState(prev => ({ ...prev, isRetrying: attempt > 0, retryCount: attempt }));
          
          const result = await operation(...args);
          
          // Success - reset state
          setState({ isRetrying: false, retryCount: 0, lastError: null });
          return result as Awaited<ReturnType<T>>;
        } catch (error) {
          setState(prev => ({ ...prev, lastError: error }));
          
          // Check if we should retry
          if (attempt < maxRetries && retryCondition(error)) {
            attempt++;
            
            // Call onRetry callback
            onRetry?.(attempt, error);
            
            // If offline, wait for connection
            if (!isOnline) {
              setState(prev => ({ ...prev, isRetrying: false }));
              
              return new Promise<Awaited<ReturnType<T>>>((resolve, reject) => {
                executeWhenOnline(async () => {
                  try {
                    const result = await attemptOperation();
                    resolve(result);
                  } catch (retryError) {
                    reject(retryError);
                  }
                });
              });
            }
            
            // Wait before retrying
            await new Promise(resolve => setTimeout(resolve, delay));
            delay = Math.min(delay * backoffMultiplier, maxDelay);
            
            return attemptOperation();
          } else {
            // Max retries reached or shouldn't retry
            setState(prev => ({ ...prev, isRetrying: false }));
            
            if (attempt >= maxRetries) {
              onMaxRetriesReached?.(error);
            }
            
            throw error;
          }
        }
      };

      return attemptOperation();
    },
    [
      operation,
      maxRetries,
      initialDelay,
      backoffMultiplier,
      maxDelay,
      retryCondition,
      onRetry,
      onMaxRetriesReached,
      handleApiError,
      isOnline,
      executeWhenOnline,
    ]
  );

  const reset = useCallback(() => {
    setState({ isRetrying: false, retryCount: 0, lastError: null });
  }, []);

  return {
    execute: executeWithRetry,
    ...state,
    reset,
  };
}; 