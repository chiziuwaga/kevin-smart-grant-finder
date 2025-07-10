import {
    Error as ErrorIcon,
    Info as InfoIcon,
    Refresh as RefreshIcon,
    Schedule as ScheduleIcon,
    CheckCircle as SuccessIcon,
    PlayArrow as TriggerIcon,
    Warning as WarningIcon
} from '@mui/icons-material';
import {
    Alert,
    Box,
    Button,
    Card,
    CardContent,
    Chip,
    CircularProgress,
    Divider,
    Grid,
    LinearProgress,
    List,
    ListItem,
    ListItemIcon,
    ListItemText,
    Typography,
    Collapse
} from '@mui/material';
import { format, formatDistanceToNow } from 'date-fns';
import { useSnackbar } from 'notistack';
import { useCallback, useEffect, useState } from 'react';

/**
 * Cron Job Status Widget
 * Monitors Heroku Scheduler health and automated search runs
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

  const getHealthIcon = (health) => {
    switch (health) {
      case 'healthy': return <SuccessIcon />;
      case 'warning': return <WarningIcon />;
      case 'error': return <ErrorIcon />;
      default: return <InfoIcon />;
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent>
          <Box display="flex" alignItems="center" gap={2}>
            <CircularProgress size={24} />
            <Typography>Loading scheduler status...</Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  if (!schedulerStatus) {
    return (
      <Card>
        <CardContent>
          <Alert severity="error">
            Failed to load scheduler status. Please try refreshing.
          </Alert>
        </CardContent>
      </Card>
    );
  }

  const { scheduler_health, issues, data } = schedulerStatus;

  return (
    <Card>
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
          <Box display="flex" alignItems="center" gap={2}>
            <ScheduleIcon color="primary" />
            <Typography variant="h6">
              Automated Search Status
            </Typography>
          </Box>        <Box display="flex" gap={1}>
          <Button
            size="small"
            startIcon={<RefreshIcon />}
            onClick={fetchSchedulerStatus}
            disabled={loading}
          >
            Refresh
          </Button>
          <Button
            size="small"
            variant="contained"
            startIcon={triggering ? <CircularProgress size={16} color="inherit" /> : <TriggerIcon />}
            onClick={triggerManualSearch}
            disabled={triggering}
            sx={{ 
              minWidth: 120,
              bgcolor: triggering ? 'primary.main' : 'primary.main',
              '&:hover': {
                bgcolor: triggering ? 'primary.dark' : 'primary.dark'
              }
            }}
          >
            {triggering ? 'Searching...' : 'Run Grant Search'}
          </Button>
        </Box>

        {/* Manual Search Progress */}
        <Collapse in={searchActive}>
          <Box sx={{ mt: 2, p: 2, bgcolor: 'action.hover', borderRadius: 1 }}>
            <Typography variant="subtitle2" gutterBottom color="primary">
              Manual Grant Search in Progress
            </Typography>
            <LinearProgress 
              variant="determinate" 
              value={searchProgress} 
              sx={{ mb: 1, height: 6, borderRadius: 3 }}
            />
            <Typography variant="body2" color="text.secondary">
              {searchStep}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Progress: {Math.round(searchProgress)}%
            </Typography>
          </Box>
        </Collapse>
        </Box>

        {/* Overall Health Status */}
        <Box display="flex" alignItems="center" gap={2} mb={2}>
          <Chip
            icon={getHealthIcon(scheduler_health)}
            label={`Scheduler ${scheduler_health}`}
            color={getHealthColor(scheduler_health)}
            variant="outlined"
          />
        </Box>

        {/* Issues Alert */}
        {issues && issues.length > 0 && (
          <Alert 
            severity={scheduler_health === 'error' ? 'error' : 'warning'} 
            sx={{ mb: 2 }}
          >
            <Typography variant="subtitle2" gutterBottom>
              Issues Detected:
            </Typography>
            <List dense>
              {issues.map((issue, index) => (
                <ListItem key={index} sx={{ pl: 0 }}>
                  <ListItemText primary={issue} />
                </ListItem>
              ))}
            </List>
          </Alert>
        )}

        <Grid container spacing={2}>
          {/* Last Run Information */}
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" gutterBottom>
              Last Automated Run
            </Typography>
            {data.last_automated_run?.timestamp ? (
              <Box>
                <Typography variant="body2">
                  {format(new Date(data.last_automated_run.timestamp), 'MMM dd, yyyy HH:mm')}
                </Typography>
                <Typography variant="caption" color="textSecondary">
                  {formatDistanceToNow(new Date(data.last_automated_run.timestamp))} ago
                </Typography>
                <Box display="flex" gap={1} mt={1}>
                  <Chip
                    label={data.last_automated_run.status || 'Unknown'}
                    color={getHealthColor(
                      data.last_automated_run.status === 'success' ? 'healthy' : 
                      data.last_automated_run.status === 'failed' ? 'error' : 'warning'
                    )}
                    size="small"
                  />
                  {data.last_automated_run.grants_found !== undefined && (
                    <Chip
                      label={`${data.last_automated_run.grants_found} grants found`}
                      size="small"
                      variant="outlined"
                    />
                  )}
                </Box>
                {data.last_automated_run.error_message && (
                  <Alert severity="error" sx={{ mt: 1 }} variant="outlined">
                    <Typography variant="caption">
                      {data.last_automated_run.error_message}
                    </Typography>
                  </Alert>
                )}
              </Box>
            ) : (
              <Typography variant="body2" color="textSecondary">
                No automated runs found
              </Typography>
            )}
          </Grid>

          {/* Next Run Information */}
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" gutterBottom>
              Next Expected Run
            </Typography>
            {data.next_expected_run ? (
              <Box>
                <Typography variant="body2">
                  {format(new Date(data.next_expected_run), 'MMM dd, yyyy HH:mm')}
                </Typography>
                <Typography variant="caption" color="textSecondary">
                  in {formatDistanceToNow(new Date(data.next_expected_run))}
                </Typography>
              </Box>
            ) : (
              <Typography variant="body2" color="textSecondary">
                Schedule not determined
              </Typography>
            )}
          </Grid>
        </Grid>

        <Divider sx={{ my: 2 }} />

        {/* Recent Statistics */}
        <Typography variant="subtitle2" gutterBottom>
          Past Week Statistics
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={4}>
            <Box textAlign="center">
              <Typography variant="h6" color="primary">
                {data.recent_week_stats?.total_runs || 0}
              </Typography>
              <Typography variant="caption" color="textSecondary">
                Total Runs
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={4}>
            <Box textAlign="center">
              <Typography variant="h6" color="success.main">
                {data.recent_week_stats?.successful_runs || 0}
              </Typography>
              <Typography variant="caption" color="textSecondary">
                Successful
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={4}>
            <Box textAlign="center">
              <Typography variant="h6" color="info.main">
                {data.recent_week_stats?.success_rate?.toFixed(1) || 0}%
              </Typography>
              <Typography variant="caption" color="textSecondary">
                Success Rate
              </Typography>
            </Box>
          </Grid>
        </Grid>

        <Divider sx={{ my: 2 }} />

        {/* Configuration Information */}
        <Typography variant="subtitle2" gutterBottom>
          Configuration
        </Typography>
        <List dense>
          <ListItem sx={{ pl: 0 }}>
            <ListItemIcon>
              <ScheduleIcon />
            </ListItemIcon>
            <ListItemText 
              primary="Schedule"
              secondary={data.configuration?.schedule || 'Not configured'}
            />
          </ListItem>
          <ListItem sx={{ pl: 0 }}>
            <ListItemIcon>
              <InfoIcon />
            </ListItemIcon>
            <ListItemText 
              primary="Type"
              secondary={data.configuration?.type || 'Unknown'}
            />
          </ListItem>
          <ListItem sx={{ pl: 0 }}>
            <ListItemIcon>
              <InfoIcon />
            </ListItemIcon>
            <ListItemText 
              primary="Command"
              secondary={data.configuration?.command || 'Not specified'}
            />
          </ListItem>
        </List>
      </CardContent>
    </Card>
  );
};

export default CronJobStatus;
