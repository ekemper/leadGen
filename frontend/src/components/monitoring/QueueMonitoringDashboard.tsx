import React, { useState, useEffect } from 'react';
import ComponentCard from '../common/ComponentCard';
import Badge from '../ui/badge/Badge';
import Button from '../ui/button/Button';
import Alert from '../ui/alert/Alert';

interface CircuitBreakerStatus {
  service: string;
  state: 'closed' | 'open' | 'half_open';
  failure_count: number;
  last_failure_time?: string;
  last_failure_reason?: string;
  next_retry_time?: string;
}

interface QueueStatusData {
  circuit_breakers: Record<string, CircuitBreakerStatus>;
  job_counts: Record<string, number>;
  paused_jobs_by_service: Record<string, number>;
  timestamp: string;
}

interface PausedJobRecovery {
  lead_id?: string;
  campaign_id: string;
  job_id: number;
  lead_email?: string;
  paused_at?: string;
}

const QueueMonitoringDashboard: React.FC = () => {
  const [queueStatus, setQueueStatus] = useState<QueueStatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshInterval, setRefreshInterval] = useState(30000); // 30 seconds
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchQueueStatus = async () => {
    try {
      setError(null);
      const response = await fetch('/api/v1/queue/status');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setQueueStatus(data.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch queue status');
    } finally {
      setLoading(false);
    }
  };

  const pauseService = async (service: string, reason: string = 'manual_pause') => {
    try {
      const response = await fetch(`/api/v1/queue/services/${service}/pause`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ service, reason })
      });
      if (!response.ok) {
        throw new Error(`Failed to pause ${service}`);
      }
      fetchQueueStatus(); // Refresh status
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to pause ${service}`);
    }
  };

  const resumeService = async (service: string) => {
    try {
      const response = await fetch(`/api/v1/queue/services/${service}/resume`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ service })
      });
      if (!response.ok) {
        throw new Error(`Failed to resume ${service}`);
      }
      fetchQueueStatus(); // Refresh status
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to resume ${service}`);
    }
  };

  const resetCircuitBreaker = async (service: string) => {
    try {
      const response = await fetch(`/api/v1/queue/circuit-breakers/${service}/reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      if (!response.ok) {
        throw new Error(`Failed to reset circuit breaker for ${service}`);
      }
      fetchQueueStatus(); // Refresh status
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to reset circuit breaker for ${service}`);
    }
  };

  useEffect(() => {
    fetchQueueStatus();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(fetchQueueStatus, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval]);

  const getStateIcon = (state: string) => {
    switch (state) {
      case 'closed':
        return <span className="inline-block h-4 w-4 rounded-full bg-green-500"></span>;
      case 'open':
        return <span className="inline-block h-4 w-4 rounded-full bg-red-500"></span>;
      case 'half_open':
        return <span className="inline-block h-4 w-4 rounded-full bg-yellow-500"></span>;
      default:
        return <span className="inline-block h-4 w-4 rounded-full bg-gray-500"></span>;
    }
  };

  const getStateBadgeColor = (state: string): 'success' | 'warning' | 'error' | 'info' => {
    switch (state) {
      case 'closed':
        return 'success';
      case 'open':
        return 'error';
      case 'half_open':
        return 'warning';
      default:
        return 'info';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
        <span className="ml-2">Loading queue status...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-800 dark:text-white">Queue Monitoring Dashboard</h1>
        <div className="flex items-center space-x-2">
          <Button
            onClick={() => setAutoRefresh(!autoRefresh)}
            variant={autoRefresh ? "primary" : "outline"}
            size="sm"
          >
            {autoRefresh ? 'Pause' : 'Resume'} Auto-refresh
          </Button>
          <Button onClick={fetchQueueStatus} size="sm" variant="outline">
            Refresh
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="error" title="Error" message={error} />
      )}

      {queueStatus && (
        <div className="grid gap-6">
          {/* Circuit Breaker Status */}
          <ComponentCard title="Circuit Breaker Status" desc="Monitor third-party service health">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {Object.entries(queueStatus.circuit_breakers).map(([service, status]) => (
                <div key={service} className="border rounded-lg p-4 bg-white dark:bg-gray-800">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-medium text-gray-800 dark:text-white">{service}</h3>
                    {getStateIcon(status.state)}
                  </div>
                  <Badge 
                    color={getStateBadgeColor(status.state)}
                    className="mb-2"
                  >
                    {status.state.replace('_', ' ').toUpperCase()}
                  </Badge>
                  <div className="mt-2 text-sm text-gray-600 dark:text-gray-300 space-y-1">
                    <div>Failures: {status.failure_count}</div>
                    {status.last_failure_time && (
                      <div>Last Failure: {new Date(status.last_failure_time).toLocaleString()}</div>
                    )}
                    {status.last_failure_reason && (
                      <div>Reason: {status.last_failure_reason}</div>
                    )}
                  </div>
                  <div className="mt-3 space-y-2">
                    {status.state === 'open' && (
                      <Button onClick={() => resetCircuitBreaker(service)} size="sm" variant="outline">
                        Reset
                      </Button>
                    )}
                    {status.state === 'closed' ? (
                      <Button onClick={() => pauseService(service)} size="sm" variant="outline">
                        Pause
                      </Button>
                    ) : (
                      <Button onClick={() => resumeService(service)} size="sm" variant="primary">
                        Resume
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </ComponentCard>

          {/* Job Status Overview */}
          <ComponentCard title="Job Status Overview" desc="Current job distribution across all queues">
            <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-6">
              {Object.entries(queueStatus.job_counts).map(([status, count]) => (
                <div key={status} className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <div className="text-2xl font-bold text-gray-800 dark:text-white">{count}</div>
                  <div className="text-sm text-gray-600 dark:text-gray-300 capitalize">{status}</div>
                </div>
              ))}
            </div>
          </ComponentCard>

          {/* Paused Jobs by Service */}
          <ComponentCard title="Paused Jobs by Service" desc="Jobs paused due to service failures">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {Object.entries(queueStatus.paused_jobs_by_service).map(([service, count]) => (
                <div key={service} className="flex justify-between items-center p-3 border rounded bg-white dark:bg-gray-800">
                  <span className="font-medium text-gray-800 dark:text-white">{service}</span>
                  <Badge color={count > 0 ? "error" : "success"}>
                    {count} paused
                  </Badge>
                </div>
              ))}
            </div>
          </ComponentCard>

          {/* Status Footer */}
          <div className="text-sm text-gray-500 text-center">
            Last updated: {new Date(queueStatus.timestamp).toLocaleString()}
          </div>
        </div>
      )}
    </div>
  );
};

export default QueueMonitoringDashboard; 