import React from 'react';
import { useError } from '../../context/ErrorContext';
import Alert from '../ui/alert/Alert';

const ErrorDisplay: React.FC = () => {
  const { errors, removeError } = useError();

  if (errors.length === 0) {
    return null;
  }

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-w-md">
      {errors.map(error => (
        <div
          key={error.id}
          className="animate-slide-in-right"
        >
          <div className="relative">
            <Alert
              variant={error.type}
              title={error.context || 'Error'}
              message={error.message}
              showLink={!!error.action}
              linkText={error.actionLabel}
              linkHref="#"
            />
            
            {/* Custom action button */}
            {error.action && (
              <button
                onClick={error.action}
                className="absolute bottom-3 right-16 text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 underline"
              >
                {error.actionLabel}
              </button>
            )}
            
            {/* Dismiss button */}
            {error.dismissible && (
              <button
                onClick={() => removeError(error.id)}
                className="absolute top-3 right-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                aria-label="Dismiss"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

export default ErrorDisplay; 