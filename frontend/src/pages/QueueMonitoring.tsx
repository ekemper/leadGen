import React from 'react';
import QueueMonitoringDashboard from '../components/monitoring/QueueMonitoringDashboard';

const QueueMonitoring: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <QueueMonitoringDashboard />
    </div>
  );
};

export default QueueMonitoring; 