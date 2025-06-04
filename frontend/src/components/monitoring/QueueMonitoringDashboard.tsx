import React, { useState, useEffect } from 'react';
import ComponentCard from '../common/ComponentCard';
import Badge from '../ui/badge/Badge';
import Button from '../ui/button/Button';
import Alert from '../ui/alert/Alert';
import { api } from '../../config/api';

interface CircuitBreakerStatus {
  circuit_state: 'closed' | 'open' | 'half_open';
  queue_paused: boolean;
  pause_info: any | null;
  failure_count: number;
  failure_threshold: number;
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
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [operationLoading, setOperationLoading] = useState<string | null>(null);
  const [refreshInterval, setRefreshInterval] = useState(30000); // 30 seconds
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchQueueStatus = async () => {
    try {
      setError(null);
      const data = await api.get('/queue-management/status');
      setQueueStatus(data.data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch queue status';
      setError(errorMessage);
      console.error('Queue status fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const pauseService = async (service: string, reason: string = 'manual_pause') => {
    try {
      setError(null);
      setSuccessMessage(null);
      setOperationLoading(`pause-${service}`);
      
      const data = await api.post('/queue-management/pause-service', { service, reason });
      setSuccessMessage(`Successfully paused ${service} service. ${data.data?.message || ''}`);
      fetchQueueStatus(); // Refresh status
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : `Failed to pause ${service}`;
      setError(errorMessage);
      console.error(`Pause service error for ${service}:`, err);
    } finally {
      setOperationLoading(null);
    }
  };

  const resumeService = async (service: string) => {
    try {
      setError(null);
      setSuccessMessage(null);
      setOperationLoading(`resume-${service}`);
      
      const data = await api.post('/queue-management/resume-service', { service });
      setSuccessMessage(`Successfully resumed ${service} service. ${data.data?.message || ''}`);
      fetchQueueStatus(); // Refresh status
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : `Failed to resume ${service}`;
      setError(errorMessage);
      console.error(`Resume service error for ${service}:`, err);
    } finally {
      setOperationLoading(null);
    }
  };

  const resetCircuitBreaker = async (service: string) => {
    try {
      setError(null);
      setSuccessMessage(null);
      setOperationLoading(`reset-${service}`);
      
      const data = await api.post(`/queue-management/circuit-breakers/${service}/reset`);
      setSuccessMessage(`Successfully reset circuit breaker for ${service}. ${data.data?.message || ''}`);
      fetchQueueStatus(); // Refresh status
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : `Failed to reset circuit breaker for ${service}`;
      setError(errorMessage);
      console.error(`Reset circuit breaker error for ${service}:`, err);
    } finally {
      setOperationLoading(null);
    }
  };

  const resumeQueue = async () => {
    try {
      setError(null);
      setSuccessMessage(null);
      setOperationLoading('resume-queue');
      
      const data = await api.post('/queue-management/resume-queue');
      setSuccessMessage(`Successfully resumed queue system. ${data.data?.message || ''}`);
      fetchQueueStatus(); // Refresh status
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to resume queue';
      setError(errorMessage);
      console.error('Resume queue error:', err);
    } finally {
      setOperationLoading(null);
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

  // Auto-clear success messages after 5 seconds
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => setSuccessMessage(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [successMessage]);

  // Auto-clear error messages after 10 seconds
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 10000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  const getStateIcon = (circuit_state: string) => {
    switch (circuit_state) {
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

  const getStateBadgeColor = (circuit_state: string): 'success' | 'warning' | 'error' | 'info' => {
    switch (circuit_state) {
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

  // Helper function to check if any circuit breakers are open
  const hasOpenCircuitBreakers = () => {
    if (!queueStatus) return false;
    return Object.values(queueStatus.circuit_breakers).some(status => status.circuit_state === 'open');
  };

  // Helper function to get open circuit breaker services
  const getOpenCircuitBreakers = () => {
    if (!queueStatus) return [];
    return Object.entries(queueStatus.circuit_breakers)
      .filter(([_, status]) => status.circuit_state === 'open')
      .map(([service, _]) => service);
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

      {successMessage && (
        <Alert variant="success" title="Success" message={successMessage} />
      )}

      {queueStatus && (
        <div className="grid gap-6">
          {/* Manual Queue Resume Section */}
          <ComponentCard 
            title="Manual Queue Resume" 
            desc="Resume all paused campaigns and jobs through manual queue control"
          >
            <div className="space-y-4">
              <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                <h3 className="font-medium text-blue-800 dark:text-blue-200 mb-2">
                  How Campaign Resume Works
                </h3>
                <p className="text-sm text-blue-600 dark:text-blue-300 mb-3">
                  Campaigns only resume through manual queue resume action. This ensures predictable control after service failures.
                </p>
                <ul className="text-sm text-blue-600 dark:text-blue-300 space-y-1">
                  <li>• Circuit breaker events pause campaigns automatically</li>
                  <li>• Manual queue resume is the ONLY way to resume campaigns</li>
                  <li>• All circuit breakers must be closed before resuming</li>
                </ul>
              </div>

              {hasOpenCircuitBreakers() ? (
                <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
                  <h4 className="font-medium text-red-800 dark:text-red-200 mb-2">
                    ⚠️ Cannot Resume Queue
                  </h4>
                  <p className="text-sm text-red-600 dark:text-red-300 mb-2">
                    The following circuit breakers are open and must be reset first:
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {getOpenCircuitBreakers().map(service => (
                      <Badge key={service} color="error">{service}</Badge>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
                  <h4 className="font-medium text-green-800 dark:text-green-200 mb-2">
                    ✅ Ready to Resume
                  </h4>
                  <p className="text-sm text-green-600 dark:text-green-300 mb-3">
                    All circuit breakers are closed. You can safely resume the queue and all paused campaigns.
                  </p>
                  <Button 
                    onClick={resumeQueue}
                    variant="primary"
                    size="md"
                    disabled={operationLoading === 'resume-queue'}
                    className="w-full sm:w-auto"
                  >
                    {operationLoading === 'resume-queue' ? 'Resuming Queue...' : 'Resume Queue & All Campaigns'}
                  </Button>
                </div>
              )}
            </div>
          </ComponentCard>

          {/* Circuit Breaker Status */}
          <ComponentCard title="Circuit Breaker Status" desc="Monitor third-party service health">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {Object.entries(queueStatus.circuit_breakers).map(([service, status]) => (
                <div key={service} className="border rounded-lg p-4 bg-white dark:bg-gray-800">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-medium text-gray-800 dark:text-white">{service}</h3>
                    {getStateIcon(status.circuit_state)}
                  </div>
                  <Badge 
                    color={getStateBadgeColor(status.circuit_state)}
                    className="mb-2"
                  >
                    {status.circuit_state.replace('_', ' ').toUpperCase()}
                  </Badge>
                  <div className="mt-2 text-sm text-gray-600 dark:text-gray-300 space-y-1">
                    <div>Failures: {status.failure_count}</div>
                    {status.failure_threshold && (
                      <div>Failure Threshold: {status.failure_threshold}</div>
                    )}
                  </div>
                  <div className="mt-3 space-y-2">
                    {status.circuit_state === 'open' && (
                      <>
                        <Button 
                          onClick={() => resetCircuitBreaker(service)} 
                          size="sm" 
                          variant="outline"
                          disabled={operationLoading === `reset-${service}`}
                        >
                          {operationLoading === `reset-${service}` ? 'Resetting...' : 'Reset Circuit Breaker'}
                        </Button>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          Note: Resetting circuit breakers does NOT resume campaigns. Use "Resume Queue" above.
                        </p>
                      </>
                    )}
                    {status.circuit_state === 'closed' && (
                      <Button 
                        onClick={() => pauseService(service)} 
                        size="sm" 
                        variant="outline"
                        disabled={operationLoading === `pause-${service}`}
                      >
                        {operationLoading === `pause-${service}` ? 'Pausing...' : 'Pause Service'}
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