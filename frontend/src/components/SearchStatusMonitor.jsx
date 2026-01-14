import { useSnackbar } from 'notistack';
import { useCallback, useEffect, useState } from 'react';
import './SearchStatusMonitor.css';

/**
 * Real-time search monitoring component
 * Polls search status and provides immediate feedback
 */
const SearchStatusMonitor = ({
  searchRunId,
  onComplete,
  onError,
  autoRefresh = true
}) => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [polling, setPolling] = useState(false);
  const { enqueueSnackbar } = useSnackbar();

  // Fetch search status
  const fetchStatus = useCallback(async () => {
    if (!searchRunId) return;

    try {
      const response = await fetch(`/api/search-runs/live-status/${searchRunId}`);
      const data = await response.json();

      if (response.ok) {
        setStatus(data.data);
        setError(null);

        // Check if search is complete
        if (data.data.status === 'success') {
          setPolling(false);
          onComplete?.(data.data);
          enqueueSnackbar(
            `Search completed! Found ${data.data.grants_found} grants.`,
            { variant: 'success' }
          );
        } else if (data.data.status === 'failed') {
          setPolling(false);
          onError?.(data.data);
          enqueueSnackbar(
            `Search failed: ${data.data.error_message || 'Unknown error'}`,
            {
              variant: 'error',
              persist: true,
            }
          );
        }
      } else {
        throw new Error(data.detail || 'Failed to fetch search status');
      }
    } catch (err) {
      console.error('Error fetching search status:', err);
      setError(err.message);
      setPolling(false);
    } finally {
      setLoading(false);
    }
  }, [searchRunId, onComplete, onError, enqueueSnackbar]);

  // Polling effect
  useEffect(() => {
    if (!searchRunId) return;

    fetchStatus();

    if (autoRefresh && (polling || (status && status.status === 'in_progress'))) {
      const interval = setInterval(fetchStatus, 2000); // Poll every 2 seconds
      return () => clearInterval(interval);
    }
  }, [searchRunId, polling, autoRefresh, status, fetchStatus]);

  // Start polling when component mounts
  useEffect(() => {
    if (searchRunId && autoRefresh) {
      setPolling(true);
    }
  }, [searchRunId, autoRefresh]);

  const getStatusColor = (statusValue) => {
    switch (statusValue) {
      case 'success': return 'success';
      case 'failed': return 'error';
      case 'in_progress': return 'info';
      default: return 'default';
    }
  };

  const getRecoveryAction = (errorMessage) => {
    if (errorMessage?.toLowerCase().includes('rate limit')) {
      return 'Try again in a few minutes when rate limits reset.';
    }
    if (errorMessage?.toLowerCase().includes('service unavailable')) {
      return 'External service is down. We\'ll retry automatically.';
    }
    if (errorMessage?.toLowerCase().includes('authentication')) {
      return 'Please check your API credentials in settings.';
    }
    return 'Please try again or contact support if the issue persists.';
  };

  if (loading && !status) {
    return (
      <div className="search-status-loading">
        <div className="spinner"></div>
        <span>Loading search status...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`alert alert-error`}>
        <div className="alert-content">
          <strong>Error:</strong> {error}
        </div>
        <button className="btn btn-secondary btn-sm" onClick={fetchStatus}>
          <span className="icon">↻</span> Retry
        </button>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="alert alert-info">
        No search status available for run ID: {searchRunId}
      </div>
    );
  }

  return (
    <div className="search-status-card">
      <div className="search-status-header">
        <h3 className="search-status-title">Search Status</h3>
        <span className={`badge badge-${getStatusColor(status.status)}`}>
          {status.status.replace('_', ' ').toUpperCase()}
        </span>
      </div>

      {status.status === 'in_progress' && (
        <div className="search-status-progress">
          <div className="search-status-progress-info">
            <span className="search-status-progress-step">{status.current_step}</span>
            <span className="search-status-progress-percent">
              {Math.round(status.progress_percentage)}%
            </span>
          </div>
          <div className="progress-bar">
            <div
              className="progress-bar-fill"
              style={{ width: `${status.progress_percentage}%` }}
            ></div>
          </div>
        </div>
      )}

      <div className="search-status-stats">
        <div className="stat-item">
          <strong>Grants Found:</strong> {status.grants_found}
        </div>
        <div className="stat-item">
          <strong>High Priority:</strong> {status.high_priority}
        </div>
        {status.duration_seconds && (
          <div className="stat-item">
            <strong>Duration:</strong> {Math.round(status.duration_seconds)}s
          </div>
        )}
      </div>

      {status.status === 'failed' && status.error_message && (
        <div className="alert alert-error">
          <div className="alert-content">
            <div><strong>Error:</strong> {status.error_message}</div>
            <div className="alert-secondary">{getRecoveryAction(status.error_message)}</div>
          </div>
        </div>
      )}

      {status.status === 'success' && (
        <div className="alert alert-success">
          Search completed successfully! Found {status.grants_found} grants
          {status.high_priority > 0 && ` (${status.high_priority} high priority)`}.
        </div>
      )}

      {autoRefresh && status.status === 'in_progress' && (
        <div className="search-status-footer">
          <div className="auto-refresh-indicator">
            <div className="spinner spinner-sm"></div>
            <span>Auto-refreshing every 2 seconds...</span>
          </div>
          <button
            className="btn btn-text btn-sm"
            onClick={() => setPolling(false)}
          >
            Stop Auto-refresh
          </button>
        </div>
      )}

      {(!autoRefresh || (status.status !== 'in_progress' && !polling)) && (
        <button
          className="btn btn-secondary"
          onClick={fetchStatus}
        >
          <span className="icon">↻</span> Refresh Status
        </button>
      )}
    </div>
  );
};

export default SearchStatusMonitor;
