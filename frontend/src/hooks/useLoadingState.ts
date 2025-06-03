import { useState, useCallback, useRef, useEffect } from 'react';

interface LoadingStateOptions {
  minLoadingTime?: number; // Minimum time to show loading (prevents flicker)
  debounceTime?: number; // Delay before showing loading (prevents flash for fast operations)
}

interface LoadingState {
  isLoading: boolean;
  isDebouncing: boolean;
  startTime: number | null;
}

export const useLoadingState = (options: LoadingStateOptions = {}) => {
  const { minLoadingTime = 500, debounceTime = 200 } = options;
  
  const [state, setState] = useState<LoadingState>({
    isLoading: false,
    isDebouncing: false,
    startTime: null,
  });
  
  const debounceTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const minTimeTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const startLoading = useCallback(() => {
    // Clear any existing timeouts
    if (debounceTimeoutRef.current) {
      clearTimeout(debounceTimeoutRef.current);
    }
    if (minTimeTimeoutRef.current) {
      clearTimeout(minTimeTimeoutRef.current);
    }

    setState(prev => ({ ...prev, isDebouncing: true }));

    // Start debounce timer
    debounceTimeoutRef.current = setTimeout(() => {
      setState({
        isLoading: true,
        isDebouncing: false,
        startTime: Date.now(),
      });
    }, debounceTime);
  }, [debounceTime]);

  const stopLoading = useCallback(() => {
    // Clear debounce timeout if still pending
    if (debounceTimeoutRef.current) {
      clearTimeout(debounceTimeoutRef.current);
      debounceTimeoutRef.current = null;
      setState({
        isLoading: false,
        isDebouncing: false,
        startTime: null,
      });
      return;
    }

    // If loading is active, respect minimum loading time
    if (state.isLoading && state.startTime) {
      const elapsed = Date.now() - state.startTime;
      const remaining = minLoadingTime - elapsed;

      if (remaining > 0) {
        minTimeTimeoutRef.current = setTimeout(() => {
          setState({
            isLoading: false,
            isDebouncing: false,
            startTime: null,
          });
        }, remaining);
      } else {
        setState({
          isLoading: false,
          isDebouncing: false,
          startTime: null,
        });
      }
    }
  }, [state.isLoading, state.startTime, minLoadingTime]);

  // Cleanup timeouts on unmount
  useEffect(() => {
    return () => {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
      if (minTimeTimeoutRef.current) {
        clearTimeout(minTimeTimeoutRef.current);
      }
    };
  }, []);

  return {
    isLoading: state.isLoading,
    isDebouncing: state.isDebouncing,
    startLoading,
    stopLoading,
    // Helper to wrap async operations
    withLoading: useCallback(async <T>(operation: () => Promise<T>): Promise<T> => {
      startLoading();
      try {
        const result = await operation();
        stopLoading();
        return result;
      } catch (error) {
        stopLoading();
        throw error;
      }
    }, [startLoading, stopLoading]),
  };
}; 