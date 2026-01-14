import { useSnackbar } from 'notistack';
import { useCallback, useEffect, useState } from 'react';
import apiClient from 'api/apiClient';
import LoaderOverlay from 'components/common/LoaderOverlay';
import './SearchHistoryTab.css';

const SearchHistoryTab = () => {
  const { enqueueSnackbar } = useSnackbar();
  const [loading, setLoading] = useState(true);
  const [searchRuns, setSearchRuns] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [latestAutomated, setLatestAutomated] = useState(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [total, setTotal] = useState(0);

  const fetchSearchRuns = useCallback(async () => {
    const filter = { days_back: 30 };
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
  }, [page, rowsPerPage, enqueueSnackbar]);

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

  const handleChangePage = (newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'success':
        return '✓';
      case 'failed':
        return '✗';
      case 'partial':
        return '⚠';
      case 'in_progress':
        return '⏳';
      default:
        return 'ℹ';
    }
  };

  const getStatusColor = (status) => {
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

  const getRunTypeIcon = (runType) => {
    switch (runType) {
      case 'automated':
      case 'scheduled':
        return '🤖';
      case 'manual':
        return '👤';
      default:
        return '▶';
    }
  };

  const formatDuration = (seconds) => {
    if (!seconds) return 'N/A';
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
  };

  const formatDateTime = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const getHealthColor = (health) => {
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

  const totalPages = Math.ceil(total / rowsPerPage);

  return (
    <div className="search-history-container">
      {/* Statistics Cards */}
      {statistics && (
        <div className="stats-cards">
          <div className="stat-card">
            <div className="stat-value stat-value-primary">
              {statistics.total_runs}
            </div>
            <div className="stat-label">Total Runs (7 days)</div>
          </div>
          <div className="stat-card">
            <div className="stat-value stat-value-success">
              {statistics.success_rate.toFixed(1)}%
            </div>
            <div className="stat-label">Success Rate</div>
          </div>
          <div className="stat-card">
            <div className="stat-value stat-value-info">
              {statistics.average_grants_found.toFixed(1)}
            </div>
            <div className="stat-label">Avg Grants Found</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">
              {formatDuration(statistics.average_duration_seconds)}
            </div>
            <div className="stat-label">Avg Duration</div>
          </div>
        </div>
      )}

      {/* Latest Automated Run Status */}
      {latestAutomated && (
        <div className={`alert alert-${getHealthColor(latestAutomated.health)}`}>
          <div className="alert-content">
            <strong>Latest Automated Run:</strong> {latestAutomated.message}
            {latestAutomated.data && (
              <div className="alert-details">
                {formatDateTime(latestAutomated.data.timestamp)} -
                Found {latestAutomated.data.grants_found} grants
                ({latestAutomated.data.high_priority} high priority)
              </div>
            )}
          </div>
          <button className="btn btn-icon btn-sm" onClick={fetchLatestAutomated}>
            <span className="icon">↻</span>
          </button>
        </div>
      )}

      {/* Search Runs Table */}
      <div className="search-history-card">
        <div className="search-history-header">
          <div className="search-history-title">
            <span className="icon">📜</span>
            <h3>Search Run History</h3>
          </div>
          <button className="btn btn-icon" onClick={fetchSearchRuns}>
            <span className="icon">↻</span>
          </button>
        </div>

        <LoaderOverlay loading={loading} height="400px">
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Type</th>
                  <th>Timestamp</th>
                  <th>Query/Filter</th>
                  <th className="text-center">Grants Found</th>
                  <th className="text-center">High Priority</th>
                  <th className="text-center">Duration</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody>
                {searchRuns.map((run) => (
                  <tr key={run.id}>
                    <td>
                      <div className="status-cell">
                        <span className={`badge badge-${getStatusColor(run.status)}`}>
                          {getStatusIcon(run.status)} {run.status}
                        </span>
                      </div>
                    </td>
                    <td>
                      <div className="type-cell">
                        <span className="type-icon">{getRunTypeIcon(run.run_type)}</span>
                        <span className="badge badge-outlined">{run.run_type}</span>
                      </div>
                    </td>
                    <td className="timestamp-cell">
                      {formatDateTime(run.timestamp)}
                    </td>
                    <td className="query-cell">
                      {run.search_query || JSON.stringify(run.search_filters || {})}
                    </td>
                    <td className="text-center font-weight-medium">
                      {run.grants_found}
                    </td>
                    <td className="text-center font-weight-medium text-primary">
                      {run.high_priority}
                    </td>
                    <td className="text-center">
                      {formatDuration(run.duration_seconds)}
                    </td>
                    <td>
                      {run.error_message && (
                        <span
                          className="badge badge-error badge-tooltip"
                          title={run.error_message}
                        >
                          Error
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
                {searchRuns.length === 0 && !loading && (
                  <tr>
                    <td colSpan="8" className="text-center text-muted">
                      No search runs found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="table-pagination">
            <div className="pagination-info">
              Showing {page * rowsPerPage + 1}-{Math.min((page + 1) * rowsPerPage, total)} of {total}
            </div>
            <div className="pagination-controls">
              <label className="pagination-label">
                Rows per page:
                <select
                  className="pagination-select"
                  value={rowsPerPage}
                  onChange={handleChangeRowsPerPage}
                >
                  <option value={5}>5</option>
                  <option value={10}>10</option>
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                </select>
              </label>
              <div className="pagination-buttons">
                <button
                  className="btn btn-icon btn-sm"
                  onClick={() => handleChangePage(page - 1)}
                  disabled={page === 0}
                >
                  ‹
                </button>
                <span className="pagination-page">
                  Page {page + 1} of {totalPages || 1}
                </span>
                <button
                  className="btn btn-icon btn-sm"
                  onClick={() => handleChangePage(page + 1)}
                  disabled={page >= totalPages - 1}
                >
                  ›
                </button>
              </div>
            </div>
          </div>
        </LoaderOverlay>
      </div>
    </div>
  );
};

export default SearchHistoryTab;
