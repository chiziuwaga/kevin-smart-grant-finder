import {
    CheckCircle as CheckCircleIcon,
    Computer as ComputerIcon,
    Error as ErrorIcon,
    History as HistoryIcon,
    Info as InfoIcon,
    Person as PersonIcon,
    PlayArrow as PlayArrowIcon,
    Refresh as RefreshIcon,
    Schedule as ScheduleIcon,
    Warning as WarningIcon
} from '@mui/icons-material';
import {
    Alert,
    Box,
    Card,
    CardContent,
    Chip,
    Grid,
    IconButton,
    Paper,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TablePagination,
    TableRow,
    Tooltip,
    Typography
} from '@mui/material';
import { useSnackbar } from 'notistack';
import React, { useCallback, useEffect, useState } from 'react';
import apiClient from 'api/apiClient';
import LoaderOverlay from 'components/common/LoaderOverlay';

const SearchHistoryTab = () => {
  const { enqueueSnackbar } = useSnackbar();
  const [loading, setLoading] = useState(true);
  const [searchRuns, setSearchRuns] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [latestAutomated, setLatestAutomated] = useState(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState({ days_back: 30 });

  const fetchSearchRuns = useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiClient.getSearchRuns({
        page: page + 1,
        page_size: rowsPerPage,
        ...filter
      });
      
      setSearchRuns(response.items);
      setTotal(response.total);
    } catch (error) {
      console.error('Failed to fetch search runs:', error);
      enqueueSnackbar('Failed to load search history', { variant: 'error' });
    } finally {
      setLoading(false);
    }
  }, [page, rowsPerPage, filter, enqueueSnackbar]);

  const fetchStatistics = useCallback(async () => {
    try {
      const response = await apiClient.getSearchRunStatistics(7);
      setStatistics(response.data);
    } catch (error) {
      console.error('Failed to fetch statistics:', error);
    }
  }, []);

  const fetchLatestAutomated = useCallback(async () => {
    try {
      const response = await apiClient.getLatestAutomatedRun();
      setLatestAutomated(response);
    } catch (error) {
      console.error('Failed to fetch latest automated run:', error);
    }
  }, []);

  useEffect(() => {
    fetchSearchRuns();
    fetchStatistics();
    fetchLatestAutomated();
  }, [fetchSearchRuns, fetchStatistics, fetchLatestAutomated]);

  const handleChangePage = (_: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircleIcon color="success" />;
      case 'failed':
        return <ErrorIcon color="error" />;
      case 'partial':
        return <WarningIcon color="warning" />;
      case 'in_progress':
        return <ScheduleIcon color="info" />;
      default:
        return <InfoIcon />;
    }
  };

  const getStatusColor = (status: string): 'success' | 'error' | 'warning' | 'info' | 'default' => {
    switch (status) {
      case 'success':
        return 'success';
      case 'failed':
        return 'error';
      case 'partial':
        return 'warning';
      case 'in_progress':
        return 'info';
      default:
        return 'default';
    }
  };

  const getRunTypeIcon = (runType: string) => {
    switch (runType) {
      case 'automated':
      case 'scheduled':
        return <ComputerIcon />;
      case 'manual':
        return <PersonIcon />;
      default:
        return <PlayArrowIcon />;
    }
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'N/A';
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const getHealthColor = (health?: string) => {
    switch (health) {
      case 'healthy':
        return 'success';
      case 'error':
        return 'error';
      case 'warning':
        return 'warning';
      default:
        return 'info';
    }
  };

  return (
    <Box>
      {/* Statistics Cards */}
      {statistics && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Paper sx={{ p: 2, textAlign: 'center' }}>
              <Typography variant="h4" color="primary">
                {statistics.total_runs}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Total Runs (7 days)
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Paper sx={{ p: 2, textAlign: 'center' }}>
              <Typography variant="h4" color="success.main">
                {statistics.success_rate.toFixed(1)}%
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Success Rate
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Paper sx={{ p: 2, textAlign: 'center' }}>
              <Typography variant="h4" color="info.main">
                {statistics.average_grants_found.toFixed(1)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Avg Grants Found
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Paper sx={{ p: 2, textAlign: 'center' }}>
              <Typography variant="h4" color="text.primary">
                {formatDuration(statistics.average_duration_seconds)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Avg Duration
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      )}

      {/* Latest Automated Run Status */}
      {latestAutomated && (
        <Alert 
          severity={getHealthColor(latestAutomated.health)} 
          sx={{ mb: 3 }}
          action={
            <Tooltip title="Refresh Status">
              <IconButton onClick={fetchLatestAutomated} size="small">
                <RefreshIcon />
              </IconButton>
            </Tooltip>
          }
        >
          <Typography variant="subtitle2">
            Latest Automated Run: {latestAutomated.message}
          </Typography>
          {latestAutomated.data && (
            <Typography variant="body2">
              {formatDateTime(latestAutomated.data.timestamp)} - 
              Found {latestAutomated.data.grants_found} grants 
              ({latestAutomated.data.high_priority} high priority)
            </Typography>
          )}
        </Alert>
      )}

      {/* Search Runs Table */}
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <HistoryIcon sx={{ mr: 1 }} />
            <Typography variant="h6">Search Run History</Typography>
            <Box sx={{ flexGrow: 1 }} />
            <Tooltip title="Refresh">
              <IconButton onClick={fetchSearchRuns}>
                <RefreshIcon />
              </IconButton>
            </Tooltip>
          </Box>

          <LoaderOverlay loading={loading}>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Status</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Timestamp</TableCell>
                    <TableCell>Query/Filter</TableCell>
                    <TableCell align="center">Grants Found</TableCell>
                    <TableCell align="center">High Priority</TableCell>
                    <TableCell align="center">Duration</TableCell>
                    <TableCell>Error</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {searchRuns.map((run) => (
                    <TableRow key={run.id} hover>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {getStatusIcon(run.status)}
                          <Chip 
                            label={run.status} 
                            size="small" 
                            color={getStatusColor(run.status)}
                            variant="outlined"
                          />
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {getRunTypeIcon(run.run_type)}
                          <Chip 
                            label={run.run_type} 
                            size="small" 
                            variant="outlined"
                          />
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {formatDateTime(run.timestamp)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ maxWidth: 200 }}>
                          {run.search_query || JSON.stringify(run.search_filters || {})}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2" fontWeight="medium">
                          {run.grants_found}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2" fontWeight="medium" color="primary">
                          {run.high_priority}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2">
                          {formatDuration(run.duration_seconds)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        {run.error_message && (
                          <Tooltip title={run.error_message}>
                            <Chip 
                              label="Error" 
                              size="small" 
                              color="error" 
                              variant="outlined"
                            />
                          </Tooltip>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                  {searchRuns.length === 0 && !loading && (
                    <TableRow>
                      <TableCell colSpan={8} align="center">
                        <Typography variant="body2" color="text.secondary">
                          No search runs found
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>

            <TablePagination
              rowsPerPageOptions={[5, 10, 25, 50]}
              component="div"
              count={total}
              rowsPerPage={rowsPerPage}
              page={page}
              onPageChange={handleChangePage}
              onRowsPerPageChange={handleChangeRowsPerPage}
            />
          </LoaderOverlay>
        </CardContent>
      </Card>
    </Box>
  );
};

export default SearchHistoryTab;
