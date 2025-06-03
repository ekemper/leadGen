import React from 'react';
import { useNetwork } from '../../context/NetworkContext';

const NetworkStatus: React.FC = () => {
  const { isOnline, isSlowConnection, lastOnline } = useNetwork();

  if (isOnline && !isSlowConnection) {
    return null; // Don't show anything when everything is fine
  }

  const getStatusInfo = () => {
    if (!isOnline) {
      return {
        color: 'bg-red-500',
        text: 'Offline',
        description: lastOnline 
          ? `Last online: ${lastOnline.toLocaleTimeString()}`
          : 'No connection',
      };
    }
    
    if (isSlowConnection) {
      return {
        color: 'bg-yellow-500',
        text: 'Slow Connection',
        description: 'Some features may be limited',
      };
    }

    return null;
  };

  const statusInfo = getStatusInfo();
  if (!statusInfo) return null;

  return (
    <div className="fixed bottom-4 left-4 z-50">
      <div className="flex items-center gap-2 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg">
        <div className={`w-2 h-2 rounded-full ${statusInfo.color} ${!isOnline ? 'animate-pulse' : ''}`} />
        <div className="text-sm">
          <div className="font-medium text-gray-900 dark:text-white">
            {statusInfo.text}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {statusInfo.description}
          </div>
        </div>
      </div>
    </div>
  );
};

export default NetworkStatus; 