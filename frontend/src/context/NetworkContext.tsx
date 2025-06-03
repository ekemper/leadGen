import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { toast } from 'react-toastify';

interface NetworkContextType {
  isOnline: boolean;
  isSlowConnection: boolean;
  retryCount: number;
  lastOnline: Date | null;
  checkConnection: () => Promise<boolean>;
  executeWhenOnline: (callback: () => Promise<void>) => Promise<void>;
}

const NetworkContext = createContext<NetworkContextType | undefined>(undefined);

interface NetworkProviderProps {
  children: ReactNode;
}

export const NetworkProvider: React.FC<NetworkProviderProps> = ({ children }) => {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [isSlowConnection, setIsSlowConnection] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [lastOnline, setLastOnline] = useState<Date | null>(new Date());
  const [hasShownOfflineToast, setHasShownOfflineToast] = useState(false);
  const [queuedActions, setQueuedActions] = useState<(() => Promise<void>)[]>([]);

  const checkConnection = useCallback(async (): Promise<boolean> => {
    try {
      const startTime = Date.now();
      const response = await fetch('/api/v1/health', {
        method: 'HEAD',
        cache: 'no-cache',
      });
      const endTime = Date.now();
      const latency = endTime - startTime;
      
      setIsSlowConnection(latency > 2000);
      
      if (response.ok) {
        setIsOnline(true);
        setLastOnline(new Date());
        setRetryCount(0);
        return true;
      }
      return false;
    } catch (error) {
      setIsOnline(false);
      return false;
    }
  }, []);

  const executeWhenOnline = useCallback(async (callback: () => Promise<void>) => {
    if (isOnline) {
      await callback();
    } else {
      setQueuedActions(prev => [...prev, callback]);
      toast.info('Action will be executed when connection is restored');
    }
  }, [isOnline]);

  const executeQueuedActions = useCallback(async () => {
    if (queuedActions.length > 0 && isOnline) {
      const actions = [...queuedActions];
      setQueuedActions([]);
      
      for (const action of actions) {
        try {
          await action();
        } catch (error) {
          console.error('Failed to execute queued action:', error);
        }
      }
      
      if (actions.length > 0) {
        toast.success(`Executed ${actions.length} queued action(s)`);
      }
    }
  }, [queuedActions, isOnline]);

  // Handle online/offline events
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      setLastOnline(new Date());
      setHasShownOfflineToast(false);
      toast.success('Connection restored');
      
      // Check actual connectivity
      checkConnection();
    };

    const handleOffline = () => {
      setIsOnline(false);
      if (!hasShownOfflineToast) {
        toast.warn('You are offline. Some features may be limited.');
        setHasShownOfflineToast(true);
      }
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [checkConnection, hasShownOfflineToast]);

  // Execute queued actions when coming back online
  useEffect(() => {
    if (isOnline) {
      executeQueuedActions();
    }
  }, [isOnline, executeQueuedActions]);

  // Periodic connection check
  useEffect(() => {
    const interval = setInterval(() => {
      if (!isOnline) {
        checkConnection().then(isConnected => {
          if (isConnected && !isOnline) {
            setIsOnline(true);
            setLastOnline(new Date());
          }
        });
      }
    }, 30000); // Check every 30 seconds when offline

    return () => clearInterval(interval);
  }, [isOnline, checkConnection]);

  const value: NetworkContextType = {
    isOnline,
    isSlowConnection,
    retryCount,
    lastOnline,
    checkConnection,
    executeWhenOnline,
  };

  return (
    <NetworkContext.Provider value={value}>
      {children}
    </NetworkContext.Provider>
  );
};

export const useNetwork = (): NetworkContextType => {
  const context = useContext(NetworkContext);
  if (!context) {
    throw new Error('useNetwork must be used within a NetworkProvider');
  }
  return context;
}; 