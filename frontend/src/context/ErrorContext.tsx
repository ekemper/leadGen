import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { toast } from 'react-toastify';
import { logger } from '../utils/logger';

export interface AppError {
  id: string;
  message: string;
  type: 'error' | 'warning' | 'info';
  timestamp: Date;
  context?: string;
  action?: () => void;
  actionLabel?: string;
  dismissible?: boolean;
  autoDismiss?: boolean;
  duration?: number;
}

interface ErrorContextType {
  errors: AppError[];
  addError: (error: Omit<AppError, 'id' | 'timestamp'>) => void;
  removeError: (id: string) => void;
  clearErrors: () => void;
  handleApiError: (error: any, context?: string, showToast?: boolean) => void;
  handleRetryableError: (error: any, retryAction: () => void, context?: string) => void;
}

const ErrorContext = createContext<ErrorContextType | undefined>(undefined);

interface ErrorProviderProps {
  children: ReactNode;
}

export const ErrorProvider: React.FC<ErrorProviderProps> = ({ children }) => {
  const [errors, setErrors] = useState<AppError[]>([]);

  const addError = useCallback((errorData: Omit<AppError, 'id' | 'timestamp'>) => {
    const error: AppError = {
      ...errorData,
      id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
      timestamp: new Date(),
      dismissible: errorData.dismissible ?? true,
      autoDismiss: errorData.autoDismiss ?? true,
      duration: errorData.duration ?? 5000,
    };

    setErrors(prev => [...prev, error]);

    // Auto-dismiss if enabled
    if (error.autoDismiss) {
      setTimeout(() => {
        removeError(error.id);
      }, error.duration);
    }
  }, []);

  const removeError = useCallback((id: string) => {
    setErrors(prev => prev.filter(error => error.id !== id));
  }, []);

  const clearErrors = useCallback(() => {
    setErrors([]);
  }, []);

  const handleApiError = useCallback((error: any, context?: string, showToast: boolean = true) => {
    const message = error?.response?.data?.message || error?.message || 'An unexpected error occurred';
    
    if (showToast) {
      // Show toast for immediate feedback
      if (error?.response?.status >= 500) {
        toast.error('Server error. Please try again later.');
      } else if (error?.response?.status === 404) {
        toast.error('Resource not found.');
      } else if (error?.response?.status === 403) {
        toast.error('Access denied.');
      } else if (error?.response?.status === 401) {
        toast.error('Please log in again.');
      } else {
        toast.error(message);
      }
    }

    // Add to error context for persistent display
    addError({
      message,
      type: 'error',
      context: context || 'API Error',
      autoDismiss: true,
    });

    // Log to logger
    try {
      logger.logError(error, { context, apiError: true });
    } catch (logError) {
      console.error('Failed to log error:', logError);
    }
  }, [addError]);

  const handleRetryableError = useCallback((error: any, retryAction: () => void, context?: string) => {
    const message = error?.message || 'Operation failed';
    
    addError({
      message,
      type: 'error',
      context: context || 'Retryable Error',
      action: retryAction,
      actionLabel: 'Retry',
      autoDismiss: false,
    });

    // Also show a toast
    toast.error(`${message}. Click retry to try again.`, {
      onClick: retryAction,
    });
  }, [addError]);

  const value: ErrorContextType = {
    errors,
    addError,
    removeError,
    clearErrors,
    handleApiError,
    handleRetryableError,
  };

  return (
    <ErrorContext.Provider value={value}>
      {children}
    </ErrorContext.Provider>
  );
};

export const useError = (): ErrorContextType => {
  const context = useContext(ErrorContext);
  if (!context) {
    throw new Error('useError must be used within an ErrorProvider');
  }
  return context;
}; 