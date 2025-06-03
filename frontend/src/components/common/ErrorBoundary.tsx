import React, { Component, ReactNode, ErrorInfo } from 'react';
import { logger } from '../../utils/logger';
import Button from '../ui/button/Button';
import Alert from '../ui/alert/Alert';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  showDetails?: boolean;
  allowRetry?: boolean;
  context?: string;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
  retryCount: number;
}

class ErrorBoundary extends Component<Props, State> {
  private maxRetries = 3;

  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      retryCount: 0,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });
    
    // Log the error
    logger.logError(error, { 
      errorInfo, 
      context: this.props.context || 'ErrorBoundary',
      retryCount: this.state.retryCount,
    });

    // Call custom error handler
    this.props.onError?.(error, errorInfo);
  }

  handleRetry = () => {
    if (this.state.retryCount < this.maxRetries) {
      this.setState(prevState => ({
        hasError: false,
        error: undefined,
        errorInfo: undefined,
        retryCount: prevState.retryCount + 1,
      }));
    }
  };

  handleReload = () => {
    window.location.reload();
  };

  handleReportError = () => {
    const { error, errorInfo } = this.state;
    const errorReport = {
      message: error?.message,
      stack: error?.stack,
      componentStack: errorInfo?.componentStack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      context: this.props.context,
    };

    // You could send this to your error reporting service
    console.error('Error Report:', errorReport);
    
    // Copy to clipboard for easy reporting
    navigator.clipboard?.writeText(JSON.stringify(errorReport, null, 2));
    alert('Error details copied to clipboard');
  };

  render() {
    if (this.state.hasError) {
      const { allowRetry = true, showDetails = false, fallback } = this.props;
      const { error, retryCount } = this.state;
      const canRetry = allowRetry && retryCount < this.maxRetries;

      if (fallback) {
        return fallback;
      }

      return (
        <div className="min-h-[400px] flex items-center justify-center p-6">
          <div className="max-w-lg w-full">
            <Alert
              variant="error"
              title="Something went wrong"
              message="An unexpected error occurred. Please try refreshing the page or contact support if the problem persists."
            />
            
            <div className="mt-6 space-y-4">
              <div className="flex flex-wrap gap-3">
                {canRetry && (
                  <Button
                    variant="primary"
                    onClick={this.handleRetry}
                  >
                    Try Again {retryCount > 0 && `(${retryCount}/${this.maxRetries})`}
                  </Button>
                )}
                
                <Button
                  variant="outline"
                  onClick={this.handleReload}
                >
                  Refresh Page
                </Button>
                
                <Button
                  variant="outline"
                  onClick={() => window.history.back()}
                >
                  Go Back
                </Button>
              </div>

              {showDetails && error && (
                <div className="mt-6">
                  <details className="group">
                    <summary className="cursor-pointer text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200">
                      Show Error Details
                    </summary>
                    <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                      <div className="text-sm space-y-2">
                        <div>
                          <strong>Error:</strong> {error.message}
                        </div>
                        {error.stack && (
                          <div>
                            <strong>Stack Trace:</strong>
                            <pre className="mt-2 text-xs overflow-auto max-h-40 bg-gray-100 dark:bg-gray-900 p-2 rounded">
                              {error.stack}
                            </pre>
                          </div>
                        )}
                      </div>
                      <Button
                        variant="outline"
                        onClick={this.handleReportError}
                        className="mt-4"
                      >
                        Copy Error Details
                      </Button>
                    </div>
                  </details>
                </div>
              )}

              <div className="text-xs text-gray-500 dark:text-gray-400">
                If this error persists, please{' '}
                <button
                  onClick={this.handleReportError}
                  className="underline hover:text-gray-700 dark:hover:text-gray-300"
                >
                  report it
                </button>
                {' '}to our support team.
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary; 