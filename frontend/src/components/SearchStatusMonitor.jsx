import { Refresh as RefreshIcon } from '@mui/icons-material';
import {
    Alert,
    Box,
    Button,
    Card,
    CardContent,
    Chip,
    CircularProgress,
    LinearProgress,
    Typography
} from '@mui/material';
import { useSnackbar } from 'notistack';
import { useCallback, useEffect, useState } from 'react';

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
              action: (
                <Button 
                  color="inherit" 
                  size="small" 
                  onClick={() => window.location.reload()}
                >
                  Retry
                </Button>
              )
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
      <Box display="flex" alignItems="center" gap={2}>
        <CircularProgress size={20} />
        <Typography variant="body2">Loading search status...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert 
        severity="error" 
        action={
          <Button 
            color="inherit" 
            size="small" 
            startIcon={<RefreshIcon />}
            onClick={fetchStatus}
          >
            Retry
          </Button>
        }
      >
        Error: {error}
      </Alert>
    );
  }

  if (!status) {
    return (
      <Alert severity="info">
        No search status available for run ID: {searchRunId}
      </Alert>
    );
  }

  return (
    <Card elevation={1}>
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
          <Typography variant="h6">
            Search Status
          </Typography>
          <Chip
            label={status.status.replace('_', ' ').toUpperCase()}
            color={getStatusColor(status.status)}
            size="small"
          />
        </Box>

        {status.status === 'in_progress' && (
          <Box mb={2}>
            <Box display="flex" justifyContent="space-between" mb={1}>
              <Typography variant="body2" color="textSecondary">
                {status.current_step}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                {Math.round(status.progress_percentage)}%
              </Typography>
            </Box>
            <LinearProgress 
              variant="determinate" 
              value={status.progress_percentage} 
              sx={{ height: 8, borderRadius: 4 }}
            />
          </Box>
        )}

        <Box display="flex" gap={2} flexWrap="wrap">
          <Typography variant="body2">
            <strong>Grants Found:</strong> {status.grants_found}
          </Typography>
          <Typography variant="body2">
            <strong>High Priority:</strong> {status.high_priority}
          </Typography>
          {status.duration_seconds && (
            <Typography variant="body2">
              <strong>Duration:</strong> {Math.round(status.duration_seconds)}s
            </Typography>
          )}
        </Box>

        {status.status === 'failed' && status.error_message && (
          <Alert severity="error" sx={{ mt: 2 }}>
            <Typography variant="body2" gutterBottom>
              <strong>Error:</strong> {status.error_message}
            </Typography>
            <Typography variant="body2" color="textSecondary">
              {getRecoveryAction(status.error_message)}
            </Typography>
          </Alert>
        )}

        {status.status === 'success' && (
          <Alert severity="success" sx={{ mt: 2 }}>
            Search completed successfully! Found {status.grants_found} grants
            {status.high_priority > 0 && ` (${status.high_priority} high priority)`}.
          </Alert>
        )}

        {autoRefresh && status.status === 'in_progress' && (
          <Box display="flex" alignItems="center" gap={1} mt={2}>
            <CircularProgress size={16} />
            <Typography variant="caption" color="textSecondary">
              Auto-refreshing every 2 seconds...
            </Typography>
            <Button 
              size="small" 
              onClick={() => setPolling(false)}
              sx={{ ml: 'auto' }}
            >
              Stop Auto-refresh
            </Button>
          </Box>
        )}

        {(!autoRefresh || (status.status !== 'in_progress' && !polling)) && (
          <Button
            startIcon={<RefreshIcon />}
            onClick={fetchStatus}
            size="small"
            sx={{ mt: 2 }}
          >
            Refresh Status
          </Button>
        )}
      </CardContent>
    </Card>
  );
};

export default SearchStatusMonitor;
