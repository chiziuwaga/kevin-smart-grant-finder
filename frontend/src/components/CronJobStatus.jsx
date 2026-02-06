import { format, formatDistanceToNow } from 'date-fns';
import { useSnackbar } from 'notistack';
import { useCallback, useEffect, useState } from 'react';
import './CronJobStatus.css';

/**
 * Cron Job Status Widget
 * Monitors Celery Beat health and automated search runs
 */
const CronJobStatus = () => {
  const { enqueueSnackbar } = useSnackbar();
  const [schedulerStatus, setSchedulerStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [searchProgress, setSearchProgress] = useState(0);
  const [searchActive, setSearchActive] = useState(false);
  const [searchStep, setSearchStep] = useState('');

  // Fetch scheduler status
  const fetchSchedulerStatus = useCallback(async () => {
    try {
      const response = await fetch('/api/system/scheduler-status');
      const data = await response.json();

      if (response.ok) {
        setSchedulerStatus(data);
      } else {
        throw new Error(data.detail || 'Failed to fetch scheduler status');
      }
    } catch (error) {
      console.error('Error fetching scheduler status:', error);
      enqueueSnackbar('Failed to fetch scheduler status', { variant: 'error' });
    } finally {
      setLoading(false);
    }
  }, [enqueueSnackbar]);

  // Trigger manual search
  const triggerManualSearch = async () => {
    setTriggering(true);
    setSearchActive(true);
    setSearchProgress(0);
    setSearchStep('Initializing grant search...');

    try {
      // Simulate progressive search steps for better UX
      const steps = [
        'Initializing search agents...',
        'Discovering grant opportunities...',
        'Analyzing grant eligibility...',
        'Calculating relevance scores...',
        'Updating database...'
      ];

      let progress = 0;
      const stepIncrement = 80 / steps.length; // Reserve 20% for completion

      const progressInterval = setInterval(() => {
        progress += stepIncrement;
        setSearchProgress(Math.min(progress, 80));

        const currentStepIndex = Math.floor(progress / stepIncrement) - 1;
        if (currentStepIndex >= 0 && currentStepIndex < steps.length) {
          setSearchStep(steps[currentStepIndex]);
        }
      }, 2000);

      const response = await fetch('/api/system/run-search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      const data = await response.json();
      clearInterval(progressInterval);

      if (response.ok) {
        setSearchProgress(100);
        setSearchStep('Search completed successfully!');
        enqueueSnackbar('Manual search initiated successfully', { variant: 'success' });
        // Refresh status after a delay
        setTimeout(fetchSchedulerStatus, 2000);
      } else {
        throw new Error(data.detail || 'Failed to trigger search');
      }
    } catch (error) {
      console.error('Error triggering search:', error);
      setSearchStep('Search failed');
      setSearchProgress(0);
      enqueueSnackbar('Failed to trigger manual search', { variant: 'error' });
    } finally {
      setTimeout(() => {
        setTriggering(false);
        setSearchActive(false);
        setSearchProgress(0);
        setSearchStep('');
      }, 3000);
    }
  };

  // Effects
  useEffect(() => {
    fetchSchedulerStatus();

    // Auto-refresh every 60 seconds
    const interval = setInterval(fetchSchedulerStatus, 60000);
    return () => clearInterval(interval);
  }, [fetchSchedulerStatus]);

  // Health status helpers
  const getHealthColor = (health) => {
    switch (health) {
      case 'healthy': return 'success';
      case 'warning': return 'warning';
      case 'error': return 'error';
      default: return 'default';
    }
  };

  if (loading) {
    return (
      <div className="cron-status-card">
        <div className="cron-status-loading">
          <div className="spinner"></div>
          <span>Loading scheduler status...</span>
        </div>
      </div>
    );
  }

  if (!schedulerStatus) {
    return (
      <div className="cron-status-card">
        <div className="alert alert-error">
          Failed to load scheduler status. Please try refreshing.
        </div>
      </div>
    );
  }

  const { scheduler_health, issues, data } = schedulerStatus;

  return (
    <div className="cron-status-card">
      <div className="cron-status-header">
        <div className="cron-status-title-section">
          <span className="icon">⏰</span>
          <h3>Automated Search Status</h3>
        </div>
        <div className="cron-status-actions">
          <button
            className="btn btn-secondary btn-sm"
            onClick={fetchSchedulerStatus}
            disabled={loading}
          >
            <span className="icon">↻</span> Refresh
          </button>
          <button
            className="btn btn-primary btn-sm"
            onClick={triggerManualSearch}
            disabled={triggering}
          >
            {triggering ? (
              <>
                <span className="spinner spinner-sm"></span> Searching...
              </>
            ) : (
              <>
                <span className="icon">▶</span> Run Grant Search
              </>
            )}
          </button>
        </div>
      </div>

      {/* Manual Search Progress */}
      {searchActive && (
        <div className="search-progress-section">
          <div className="search-progress-header">
            <strong>Manual Grant Search in Progress</strong>
          </div>
          <div className="progress-bar progress-bar-lg">
            <div
              className="progress-bar-fill"
              style={{ width: `${searchProgress}%` }}
            ></div>
          </div>
          <div className="search-progress-info">
            <span className="search-step">{searchStep}</span>
            <span className="search-percent">Progress: {Math.round(searchProgress)}%</span>
          </div>
        </div>
      )}

      {/* Overall Health Status */}
      <div className="cron-status-health">
        <span className={`badge badge-${getHealthColor(scheduler_health)}`}>
          {scheduler_health === 'healthy' && '✓'}
          {scheduler_health === 'warning' && '⚠'}
          {scheduler_health === 'error' && '✗'}
          {' '}Scheduler {scheduler_health}
        </span>
      </div>

      {/* Issues Alert */}
      {issues && issues.length > 0 && (
        <div className={`alert alert-${scheduler_health === 'error' ? 'error' : 'warning'}`}>
          <div className="alert-title">Issues Detected:</div>
          <ul className="issues-list">
            {issues.map((issue, index) => (
              <li key={index}>{issue}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="cron-status-grid">
        {/* Last Run Information */}
        <div className="cron-status-section">
          <h4 className="section-title">Last Automated Run</h4>
          {data.last_automated_run?.timestamp ? (
            <div className="section-content">
              <div className="stat-row">
                <span className="stat-label">Time:</span>
                <span className="stat-value">
                  {format(new Date(data.last_automated_run.timestamp), 'MMM dd, yyyy HH:mm')}
                </span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Relative:</span>
                <span className="stat-value text-muted">
                  {formatDistanceToNow(new Date(data.last_automated_run.timestamp))} ago
                </span>
              </div>
              <div className="badge-group">
                <span className={`badge badge-${getHealthColor(
                  data.last_automated_run.status === 'success' ? 'healthy' :
                  data.last_automated_run.status === 'failed' ? 'error' : 'warning'
                )}`}>
                  {data.last_automated_run.status || 'Unknown'}
                </span>
                {data.last_automated_run.grants_found !== undefined && (
                  <span className="badge badge-default">
                    {data.last_automated_run.grants_found} grants found
                  </span>
                )}
              </div>
              {data.last_automated_run.error_message && (
                <div className="alert alert-error alert-compact">
                  {data.last_automated_run.error_message}
                </div>
              )}
            </div>
          ) : (
            <div className="section-content text-muted">
              No automated runs found
            </div>
          )}
        </div>

        {/* Next Run Information */}
        <div className="cron-status-section">
          <h4 className="section-title">Next Expected Run</h4>
          {data.next_expected_run ? (
            <div className="section-content">
              <div className="stat-row">
                <span className="stat-label">Time:</span>
                <span className="stat-value">
                  {format(new Date(data.next_expected_run), 'MMM dd, yyyy HH:mm')}
                </span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Relative:</span>
                <span className="stat-value text-muted">
                  in {formatDistanceToNow(new Date(data.next_expected_run))}
                </span>
              </div>
            </div>
          ) : (
            <div className="section-content text-muted">
              Schedule not determined
            </div>
          )}
        </div>
      </div>

      <div className="cron-divider"></div>

      {/* Recent Statistics */}
      <div>
        <h4 className="section-title">Past Week Statistics</h4>
        <div className="stats-grid">
          <div className="stat-box">
            <div className="stat-value-large">{data.recent_week_stats?.total_runs || 0}</div>
            <div className="stat-label-small">Total Runs</div>
          </div>
          <div className="stat-box">
            <div className="stat-value-large stat-value-success">
              {data.recent_week_stats?.successful_runs || 0}
            </div>
            <div className="stat-label-small">Successful</div>
          </div>
          <div className="stat-box">
            <div className="stat-value-large stat-value-info">
              {data.recent_week_stats?.success_rate?.toFixed(1) || 0}%
            </div>
            <div className="stat-label-small">Success Rate</div>
          </div>
        </div>
      </div>

      <div className="cron-divider"></div>

      {/* Configuration Information */}
      <div>
        <h4 className="section-title">Configuration</h4>
        <div className="config-list">
          <div className="config-item">
            <span className="icon">⏰</span>
            <div className="config-content">
              <div className="config-label">Schedule</div>
              <div className="config-value">{data.configuration?.schedule || 'Not configured'}</div>
            </div>
          </div>
          <div className="config-item">
            <span className="icon">ℹ</span>
            <div className="config-content">
              <div className="config-label">Type</div>
              <div className="config-value">{data.configuration?.type || 'Unknown'}</div>
            </div>
          </div>
          <div className="config-item">
            <span className="icon">⚙</span>
            <div className="config-content">
              <div className="config-label">Command</div>
              <div className="config-value">{data.configuration?.command || 'Not specified'}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CronJobStatus;
