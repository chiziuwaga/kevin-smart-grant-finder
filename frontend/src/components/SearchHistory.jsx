import {
    ErrorOutline as ErrorIcon,
    Refresh as RefreshIcon,
    PlayArrow as RetryIcon,
    Schedule as ScheduleIcon,
    CheckCircle as SuccessIcon,
    Visibility as ViewIcon
} from '@mui/icons-material';
import {
    Alert,
    Box,
    Button,
    Card,
    CardContent,
    Chip,
    CircularProgress,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    FormControl,
    Grid,
    IconButton,
    InputLabel,
    MenuItem,
    Pagination,
    Paper,
    Select,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Tooltip,
    Typography
} from '@mui/material';
import { format, formatDistanceToNow } from 'date-fns';
import { useSnackbar } from 'notistack';
import { useCallback, useEffect, useState } from 'react';

/**
 * Search History Dashboard Component
 * Shows comprehensive history of all grant search runs
 */
const SearchHistory = () => {
  const { enqueueSnackbar } = useSnackbar();
  
  // State for search history
  const [searchRuns, setSearchRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [totalRuns, setTotalRuns] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  
  // Filters
  const [runTypeFilter, setRunTypeFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [daysBack, setDaysBack] = useState(30);
  
  // Analytics
  const [analytics, setAnalytics] = useState(null);
  
  // Detail modal
  const [selectedRun, setSelectedRun] = useState(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);

  // Fetch search runs
  const fetchSearchRuns = useCallback(async () => {
    setLoading(true);
    try {
      const params = {
        page,
        page_size: pageSize,
        run_type: runTypeFilter === 'all' ? undefined : runTypeFilter,
        status: statusFilter === 'all' ? undefined : statusFilter,
        days_back: daysBack
      };

      const response = await fetch(`/api/search-runs?${new URLSearchParams(params)}`);
      const data = await response.json();

      if (response.ok) {
        setSearchRuns(data.data.items || []);
        setTotalRuns(data.data.total || 0);
      } else {
        throw new Error(data.detail || 'Failed to fetch search runs');
      }
    } catch (error) {
      console.error('Error fetching search runs:', error);
      enqueueSnackbar('Failed to fetch search history', { variant: 'error' });
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, runTypeFilter, statusFilter, daysBack, enqueueSnackbar]);

  // Fetch analytics
  const fetchAnalytics = useCallback(async () => {
    try {
      const response = await fetch(`/api/search-runs/analytics?days_back=${daysBack}`);
      const data = await response.json();

      if (response.ok) {
        setAnalytics(data.data);
      }
    } catch (error) {
      console.error('Error fetching analytics:', error);
    }
  }, [daysBack]);

  // Effects
  useEffect(() => {
    fetchSearchRuns();
  }, [fetchSearchRuns]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  // Handlers
  const handleRefresh = () => {
    fetchSearchRuns();
    fetchAnalytics();
  };

  const handlePageChange = (event, newPage) => {
    setPage(newPage);
  };

  const handleViewDetails = (run) => {
    setSelectedRun(run);
    setDetailModalOpen(true);
  };

  const handleRetrySearch = async (run) => {
    try {
      // Trigger a new manual search with similar parameters
      const response = await fetch('/api/system/run-search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        enqueueSnackbar('Search retry initiated successfully', { variant: 'success' });
        // Refresh the list after a short delay
        setTimeout(fetchSearchRuns, 1000);
      } else {
        throw new Error('Failed to retry search');
      }
    } catch (error) {
      console.error('Error retrying search:', error);
      enqueueSnackbar('Failed to retry search', { variant: 'error' });
    }
  };

  // Status helpers
  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'success': return 'success';
      case 'failed': return 'error';
      case 'in_progress': return 'info';
      case 'partial': return 'warning';
      default: return 'default';
    }
  };

  const getStatusIcon = (status) => {
    switch (status?.toLowerCase()) {
      case 'success': return <SuccessIcon fontSize="small" />;
      case 'failed': return <ErrorIcon fontSize="small" />;
      case 'in_progress': return <ScheduleIcon fontSize="small" />;
      default: return null;
    }
  };

  const getRunTypeColor = (runType) => {
    return runType === 'automated' ? 'primary' : 'secondary';
  };

  return (
    <Box>
      {/* Analytics Cards */}
      {analytics && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6" color="textSecondary" gutterBottom>
                  Total Runs
                </Typography>
                <Typography variant="h4" color="primary">
                  {analytics.total_runs}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6" color="textSecondary" gutterBottom>
                  Success Rate
                </Typography>
                <Typography variant="h4" color="success.main">
                  {analytics.success_rate?.toFixed(1)}%
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6" color="textSecondary" gutterBottom>
                  Avg Grants Found
                </Typography>
                <Typography variant="h4" color="info.main">
                  {analytics.average_grants_found?.toFixed(1)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6" color="textSecondary" gutterBottom>
                  Avg Duration
                </Typography>
                <Typography variant="h4" color="text.primary">
                  {analytics.average_duration_seconds?.toFixed(1)}s
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Filters and Controls */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={6} md={2}>
            <FormControl fullWidth size="small">
              <InputLabel>Run Type</InputLabel>
              <Select
                value={runTypeFilter}
                onChange={(e) => setRunTypeFilter(e.target.value)}
                label="Run Type"
              >
                <MenuItem value="all">All Types</MenuItem>
                <MenuItem value="manual">Manual</MenuItem>
                <MenuItem value="automated">Automated</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={6} md={2}>
            <FormControl fullWidth size="small">
              <InputLabel>Status</InputLabel>
              <Select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                label="Status"
              >
                <MenuItem value="all">All Status</MenuItem>
                <MenuItem value="success">Success</MenuItem>
                <MenuItem value="failed">Failed</MenuItem>
                <MenuItem value="in_progress">In Progress</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={6} md={2}>
            <FormControl fullWidth size="small">
              <InputLabel>Time Range</InputLabel>
              <Select
                value={daysBack}
                onChange={(e) => setDaysBack(e.target.value)}
                label="Time Range"
              >
                <MenuItem value={7}>Last 7 days</MenuItem>
                <MenuItem value={30}>Last 30 days</MenuItem>
                <MenuItem value={90}>Last 90 days</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={6} md={2}>
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={handleRefresh}
              fullWidth
            >
              Refresh
            </Button>
          </Grid>
          <Grid item xs={12} md={4}>
            <Typography variant="body2" color="textSecondary">
              Showing {searchRuns.length} of {totalRuns} search runs
            </Typography>
          </Grid>
        </Grid>
      </Paper>

      {/* Search Runs Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Timestamp</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Grants Found</TableCell>
              <TableCell>High Priority</TableCell>
              <TableCell>Duration</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  <CircularProgress />
                </TableCell>
              </TableRow>
            ) : searchRuns.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  <Typography variant="body2" color="textSecondary">
                    No search runs found for the selected criteria
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              searchRuns.map((run) => (
                <TableRow key={run.id} hover>
                  <TableCell>
                    <Box>
                      <Typography variant="body2">
                        {format(new Date(run.timestamp), 'MMM dd, yyyy HH:mm')}
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        {formatDistanceToNow(new Date(run.timestamp))} ago
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={run.run_type} 
                      color={getRunTypeColor(run.run_type)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Chip 
                      icon={getStatusIcon(run.status)}
                      label={run.status} 
                      color={getStatusColor(run.status)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>{run.grants_found || 0}</TableCell>
                  <TableCell>{run.high_priority || 0}</TableCell>
                  <TableCell>
                    {run.duration_seconds ? `${run.duration_seconds.toFixed(1)}s` : '-'}
                  </TableCell>
                  <TableCell>
                    <Box display="flex" gap={1}>
                      <Tooltip title="View Details">
                        <IconButton 
                          size="small"
                          onClick={() => handleViewDetails(run)}
                        >
                          <ViewIcon />
                        </IconButton>
                      </Tooltip>
                      {run.status === 'failed' && (
                        <Tooltip title="Retry Search">
                          <IconButton 
                            size="small"
                            onClick={() => handleRetrySearch(run)}
                          >
                            <RetryIcon />
                          </IconButton>
                        </Tooltip>
                      )}
                    </Box>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Pagination */}
      {totalRuns > pageSize && (
        <Box display="flex" justifyContent="center" mt={2}>
          <Pagination
            count={Math.ceil(totalRuns / pageSize)}
            page={page}
            onChange={handlePageChange}
            color="primary"
          />
        </Box>
      )}

      {/* Detail Modal */}
      <Dialog 
        open={detailModalOpen} 
        onClose={() => setDetailModalOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Search Run Details
          {selectedRun && (
            <Chip 
              label={selectedRun.status} 
              color={getStatusColor(selectedRun.status)}
              size="small"
              sx={{ ml: 2 }}
            />
          )}
        </DialogTitle>
        <DialogContent>
          {selectedRun && (
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" gutterBottom>Run ID</Typography>
                <Typography variant="body2">{selectedRun.id}</Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" gutterBottom>Timestamp</Typography>
                <Typography variant="body2">
                  {format(new Date(selectedRun.timestamp), 'MMM dd, yyyy HH:mm:ss')}
                </Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" gutterBottom>Run Type</Typography>
                <Typography variant="body2">{selectedRun.run_type}</Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" gutterBottom>Duration</Typography>
                <Typography variant="body2">
                  {selectedRun.duration_seconds ? `${selectedRun.duration_seconds.toFixed(2)} seconds` : 'N/A'}
                </Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" gutterBottom>Grants Found</Typography>
                <Typography variant="body2">{selectedRun.grants_found || 0}</Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" gutterBottom>High Priority</Typography>
                <Typography variant="body2">{selectedRun.high_priority || 0}</Typography>
              </Grid>
              {selectedRun.error_message && (
                <Grid item xs={12}>
                  <Typography variant="subtitle2" gutterBottom>Error Message</Typography>
                  <Alert severity="error" sx={{ mt: 1 }}>
                    {selectedRun.error_message}
                  </Alert>
                </Grid>
              )}
              {selectedRun.search_filters && (
                <Grid item xs={12}>
                  <Typography variant="subtitle2" gutterBottom>Search Filters</Typography>
                  <Box component="pre" sx={{ 
                    backgroundColor: 'background.paper',
                    p: 2,
                    border: 1,
                    borderColor: 'divider',
                    borderRadius: 1,
                    fontSize: '0.875rem',
                    overflow: 'auto'
                  }}>
                    {JSON.stringify(selectedRun.search_filters, null, 2)}
                  </Box>
                </Grid>
              )}
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          {selectedRun?.status === 'failed' && (
            <Button 
              startIcon={<RetryIcon />}
              onClick={() => {
                handleRetrySearch(selectedRun);
                setDetailModalOpen(false);
              }}
            >
              Retry Search
            </Button>
          )}
          <Button onClick={() => setDetailModalOpen(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default SearchHistory;
