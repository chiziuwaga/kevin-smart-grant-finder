import { useCallback, useEffect, useState } from 'react';
import apiClient from '../api/apiClient';
import GrantCard from './GrantCard';
import GrantDetailsModal from './GrantDetailsModal';
import '../styles/swiss-theme.css';
import './Dashboard.css';

const Dashboard = () => {
  const [grants, setGrants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [savedGrants, setSavedGrants] = useState(new Set());

  // Bulk operations state
  const [selectedGrants, setSelectedGrants] = useState(new Set());
  const [bulkActionMode, setBulkActionMode] = useState(false);
  const [bulkLoading, setBulkLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  const [filters, setFilters] = useState({
    searchText: '',
    category: '',
    minOverallScore: '',
    maxOverallScore: '',
    includeExpired: false,
  });

  // Application Feedback Modal state
  const [feedbackModalOpen, setFeedbackModalOpen] = useState(false);
  const [currentGrantForFeedback, setCurrentGrantForFeedback] = useState(null);
  const [feedbackData, setFeedbackData] = useState({});
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  const [feedbackError, setFeedbackError] = useState(null);

  // Application History state
  const [applicationHistory, setApplicationHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState(null);
  const [historyModalOpen, setHistoryModalOpen] = useState(false);
  const [currentGrantForHistory, setCurrentGrantForHistory] = useState(null);
  const [historyPage, setHistoryPage] = useState(0);
  const [historyRowsPerPage, setHistoryRowsPerPage] = useState(5);

  // Grant Details Modal
  const [detailsModalOpen, setDetailsModalOpen] = useState(false);
  const [currentGrantForDetails, setCurrentGrantForDetails] = useState(null);

  const handleViewDetails = (grant) => {
    setCurrentGrantForDetails(grant);
    setDetailsModalOpen(true);
  };

  const handleCloseDetails = () => {
    setDetailsModalOpen(false);
    setCurrentGrantForDetails(null);
  };

  const fetchGrants = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const {
        searchText,
        category,
        minOverallScore,
        maxOverallScore,
        includeExpired,
        ...otherFilters
      } = filters;

      const params = {
        searchText: searchText || undefined,
        category: category || undefined,
        min_overall_score: minOverallScore ? parseFloat(minOverallScore) : undefined,
        max_overall_score: maxOverallScore ? parseFloat(maxOverallScore) : undefined,
        ...otherFilters,
      };

      const response = await apiClient.getGrants(params);
      let grantsData = response.items;

      // Client-side filtering for expired grants
      if (!includeExpired) {
        grantsData = grantsData.filter((grant) => {
          const deadline = grant.deadline || grant.deadline_date;
          if (!deadline) return true;
          return new Date(deadline) >= new Date();
        });
      }

      setGrants(grantsData);
    } catch (err) {
      setError(err.message || 'Failed to fetch grants');
    }
    setLoading(false);
  }, [filters]);

  useEffect(() => {
    fetchGrants();
  }, [fetchGrants]);

  useEffect(() => {
    const fetchSaved = async () => {
      try {
        const response = await apiClient.getSavedGrants();
        setSavedGrants(new Set(response.items.map((g) => g.id)));
      } catch (err) {
        console.error('Failed to fetch saved grants:', err);
      }
    };
    fetchSaved();
  }, []);

  const handleSaveGrant = async (grantId, save) => {
    try {
      if (save) {
        await apiClient.saveGrant(grantId);
        setSavedGrants((prev) => new Set(prev).add(grantId));
      } else {
        await apiClient.unsaveGrant(grantId);
        setSavedGrants((prev) => {
          const next = new Set(prev);
          next.delete(grantId);
          return next;
        });
      }
    } catch (err) {
      console.error(`Failed to ${save ? 'save' : 'unsave'} grant:`, err);
      setError(`Failed to ${save ? 'save' : 'unsave'} grant. Please try again.`);
    }
  };

  const handleFilterChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFilters((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSearch = () => {
    fetchGrants();
  };

  const handleClearFilters = () => {
    setFilters({
      searchText: '',
      category: '',
      minOverallScore: '',
      maxOverallScore: '',
      includeExpired: false,
    });
  };

  // Bulk operations handlers
  const handleSelectGrant = (grantId, selected) => {
    setSelectedGrants((prev) => {
      const newSet = new Set(prev);
      if (selected) {
        newSet.add(grantId);
      } else {
        newSet.delete(grantId);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    if (selectedGrants.size === grants.length) {
      setSelectedGrants(new Set());
    } else {
      setSelectedGrants(new Set(grants.map((g) => g.id)));
    }
  };

  const handleBulkSave = async () => {
    setBulkLoading(true);
    try {
      const savePromises = Array.from(selectedGrants).map((grantId) =>
        apiClient.saveGrant(grantId)
      );
      await Promise.all(savePromises);

      setSavedGrants((prev) => {
        const newSet = new Set(prev);
        selectedGrants.forEach((id) => newSet.add(id));
        return newSet;
      });

      setSelectedGrants(new Set());
      setBulkActionMode(false);
      setSuccessMessage(`Successfully saved ${selectedGrants.size} grants`);
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err) {
      setError('Failed to save selected grants');
    }
    setBulkLoading(false);
  };

  const handleBulkUnsave = async () => {
    setBulkLoading(true);
    try {
      const unsavePromises = Array.from(selectedGrants).map((grantId) =>
        apiClient.unsaveGrant(grantId)
      );
      await Promise.all(unsavePromises);

      setSavedGrants((prev) => {
        const newSet = new Set(prev);
        selectedGrants.forEach((id) => newSet.delete(id));
        return newSet;
      });

      setSelectedGrants(new Set());
      setBulkActionMode(false);
      setSuccessMessage(`Successfully unsaved ${selectedGrants.size} grants`);
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err) {
      setError('Failed to unsave selected grants');
    }
    setBulkLoading(false);
  };

  const handleBulkExportCSV = () => {
    const selectedGrantsData = grants.filter((grant) =>
      selectedGrants.has(grant.id)
    );
    const csvContent = generateCSV(selectedGrantsData);
    downloadFile(
      csvContent,
      `grants_export_${new Date().toISOString().split('T')[0]}.csv`,
      'text/csv'
    );
    setSelectedGrants(new Set());
    setBulkActionMode(false);
    setSuccessMessage(`Successfully exported ${selectedGrantsData.length} grants to CSV`);
    setTimeout(() => setSuccessMessage(''), 3000);
  };

  const generateCSV = (grantsData) => {
    const headers = ['Title', 'Funder', 'Category', 'Deadline', 'Funding Amount', 'Score', 'Source URL'];
    const rows = grantsData.map(grant => [
      grant.title || '',
      grant.funder_name || '',
      grant.category || grant.identified_sector || '',
      grant.deadline || grant.deadline_date || '',
      grant.funding_amount_display || grant.fundingAmount || '',
      grant.overall_composite_score || grant.relevanceScore || '',
      grant.source_url || ''
    ]);

    return [headers, ...rows].map(row =>
      row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')
    ).join('\n');
  };

  const downloadFile = (content, filename, mimeType) => {
    const blob = new Blob([content], { type: mimeType });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  };

  // Application Feedback Modal Handlers
  const openFeedbackModal = (grant) => {
    setCurrentGrantForFeedback(grant);
    setFeedbackData({ grant_id: grant.id });
    setFeedbackError(null);
    setFeedbackModalOpen(true);
  };

  const closeFeedbackModal = () => {
    setFeedbackModalOpen(false);
    setCurrentGrantForFeedback(null);
    setFeedbackData({});
  };

  const handleFeedbackChange = (e) => {
    const { name, value } = e.target;
    setFeedbackData((prev) => ({ ...prev, [name]: value }));
  };

  const handleFeedbackSubmit = async () => {
    if (!feedbackData.grant_id || !feedbackData.status || !feedbackData.submission_date) {
      setFeedbackError('Please fill in all required fields (status, submission date).');
      return;
    }

    setFeedbackSubmitting(true);
    setFeedbackError(null);
    try {
      await apiClient.submitApplicationFeedback(feedbackData);
      closeFeedbackModal();
      setSuccessMessage('Feedback submitted successfully!');
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err) {
      setFeedbackError(err.message || 'Failed to submit feedback.');
    }
    setFeedbackSubmitting(false);
  };

  // Application History Modal Handlers
  const fetchApplicationHistory = async (grantId) => {
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const response = await apiClient.getApplicationHistoryForGrant(grantId);
      setApplicationHistory(response.items);
    } catch (err) {
      setHistoryError(err.message || 'Failed to fetch application history.');
      setApplicationHistory([]);
    }
    setHistoryLoading(false);
  };

  const openHistoryModal = (grant) => {
    setCurrentGrantForHistory(grant);
    fetchApplicationHistory(grant.id);
    setHistoryModalOpen(true);
  };

  const closeHistoryModal = () => {
    setHistoryModalOpen(false);
    setCurrentGrantForHistory(null);
    setApplicationHistory([]);
    setHistoryPage(0);
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p className="mt-2">Loading grants...</p>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Grant Dashboard</h1>
        <div className="dashboard-actions">
          <button
            className="btn btn-primary"
            onClick={() => fetchGrants()}
            disabled={loading}
          >
            ↻ Refresh
          </button>
          <button
            className={`btn ${bulkActionMode ? 'btn-secondary' : 'btn-text'}`}
            onClick={() => setBulkActionMode(!bulkActionMode)}
          >
            {bulkActionMode ? 'Cancel Bulk Mode' : 'Bulk Actions'}
          </button>
        </div>
      </div>

      {/* Success/Error Messages */}
      {successMessage && (
        <div className="alert alert-success">
          {successMessage}
        </div>
      )}
      {error && (
        <div className="alert alert-error">
          {error}
          <button className="btn-text" onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {/* Filters */}
      <div className="card mb-3">
        <div className="card-header">
          <h3 className="card-title">Filters</h3>
        </div>
        <div className="filter-grid">
          <div className="form-group">
            <label className="label" htmlFor="searchText">Search</label>
            <input
              type="text"
              id="searchText"
              name="searchText"
              className="input"
              placeholder="Search grants..."
              value={filters.searchText}
              onChange={handleFilterChange}
            />
          </div>

          <div className="form-group">
            <label className="label" htmlFor="category">Category</label>
            <select
              id="category"
              name="category"
              className="input"
              value={filters.category}
              onChange={handleFilterChange}
            >
              <option value="">All Categories</option>
              <option value="Research">Research</option>
              <option value="Education">Education</option>
              <option value="Community">Community</option>
              <option value="Healthcare">Healthcare</option>
              <option value="Environment">Environment</option>
              <option value="Arts">Arts</option>
              <option value="Business">Business</option>
              <option value="Energy">Energy</option>
              <option value="Other">Other</option>
            </select>
          </div>

          <div className="form-group">
            <label className="label" htmlFor="minOverallScore">Min Score</label>
            <input
              type="number"
              id="minOverallScore"
              name="minOverallScore"
              className="input"
              placeholder="0"
              min="0"
              max="100"
              value={filters.minOverallScore}
              onChange={handleFilterChange}
            />
          </div>

          <div className="form-group">
            <label className="label" htmlFor="maxOverallScore">Max Score</label>
            <input
              type="number"
              id="maxOverallScore"
              name="maxOverallScore"
              className="input"
              placeholder="100"
              min="0"
              max="100"
              value={filters.maxOverallScore}
              onChange={handleFilterChange}
            />
          </div>

          <div className="form-group flex items-center">
            <label className="checkbox-label">
              <input
                type="checkbox"
                name="includeExpired"
                checked={filters.includeExpired}
                onChange={handleFilterChange}
              />
              <span>Include Expired</span>
            </label>
          </div>
        </div>

        <div className="flex gap-2 mt-3">
          <button className="btn btn-primary" onClick={handleSearch}>
            Search
          </button>
          <button className="btn btn-secondary" onClick={handleClearFilters}>
            Clear Filters
          </button>
        </div>
      </div>

      {/* Bulk Actions Bar */}
      {bulkActionMode && (
        <div className="bulk-actions-bar card mb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={selectedGrants.size === grants.length && grants.length > 0}
                  onChange={handleSelectAll}
                />
                <span>Select All ({selectedGrants.size} selected)</span>
              </label>
            </div>
            {selectedGrants.size > 0 && (
              <div className="flex gap-2">
                <button
                  className="btn btn-sm btn-primary"
                  onClick={handleBulkSave}
                  disabled={bulkLoading}
                >
                  💾 Save Selected
                </button>
                <button
                  className="btn btn-sm btn-secondary"
                  onClick={handleBulkUnsave}
                  disabled={bulkLoading}
                >
                  Remove Selected
                </button>
                <button
                  className="btn btn-sm btn-text"
                  onClick={handleBulkExportCSV}
                  disabled={bulkLoading}
                >
                  📥 Export CSV
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Grants Grid */}
      <div className="grants-grid">
        {grants.length === 0 ? (
          <div className="empty-state">
            <p>No grants found matching your criteria.</p>
            <button className="btn btn-primary mt-3" onClick={handleClearFilters}>
              Clear Filters
            </button>
          </div>
        ) : (
          grants.map((grant) => (
            <GrantCard
              key={grant.id}
              grant={grant}
              isSaved={savedGrants.has(grant.id)}
              onSave={handleSaveGrant}
              onViewDetails={handleViewDetails}
              onSelect={bulkActionMode ? handleSelectGrant : null}
              isSelected={selectedGrants.has(grant.id)}
            />
          ))
        )}
      </div>

      {/* Grant Details Modal */}
      {detailsModalOpen && currentGrantForDetails && (
        <GrantDetailsModal
          grant={currentGrantForDetails}
          open={detailsModalOpen}
          onClose={handleCloseDetails}
          onSave={handleSaveGrant}
          isSaved={savedGrants.has(currentGrantForDetails.id)}
          onProvideFeedback={openFeedbackModal}
          onViewHistory={openHistoryModal}
        />
      )}

      {/* Application Feedback Modal */}
      {feedbackModalOpen && (
        <div className="modal-backdrop" onClick={closeFeedbackModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">Provide Application Feedback</h3>
              <button className="modal-close" onClick={closeFeedbackModal}>✕</button>
            </div>
            <div className="modal-body">
              {feedbackError && <div className="alert alert-error mb-2">{feedbackError}</div>}

              <div className="form-group">
                <label className="label">Grant</label>
                <input
                  type="text"
                  className="input"
                  value={currentGrantForFeedback?.title || ''}
                  disabled
                />
              </div>

              <div className="form-group">
                <label className="label">Status *</label>
                <select
                  name="status"
                  className="input"
                  value={feedbackData.status || ''}
                  onChange={handleFeedbackChange}
                >
                  <option value="">Select status...</option>
                  <option value="submitted">Submitted</option>
                  <option value="approved">Approved</option>
                  <option value="rejected">Rejected</option>
                  <option value="in_progress">In Progress</option>
                </select>
              </div>

              <div className="form-group">
                <label className="label">Submission Date *</label>
                <input
                  type="date"
                  name="submission_date"
                  className="input"
                  value={feedbackData.submission_date || ''}
                  onChange={handleFeedbackChange}
                />
              </div>

              <div className="form-group">
                <label className="label">Notes</label>
                <textarea
                  name="notes"
                  className="input"
                  rows="4"
                  value={feedbackData.notes || ''}
                  onChange={handleFeedbackChange}
                  placeholder="Optional notes about this application..."
                />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={closeFeedbackModal}>
                Cancel
              </button>
              <button
                className="btn btn-primary"
                onClick={handleFeedbackSubmit}
                disabled={feedbackSubmitting}
              >
                {feedbackSubmitting ? 'Submitting...' : 'Submit Feedback'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Application History Modal */}
      {historyModalOpen && (
        <div className="modal-backdrop" onClick={closeHistoryModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '800px' }}>
            <div className="modal-header">
              <h3 className="modal-title">Application History</h3>
              <button className="modal-close" onClick={closeHistoryModal}>✕</button>
            </div>
            <div className="modal-body">
              {historyError && <div className="alert alert-error mb-2">{historyError}</div>}

              <h4 className="mb-2">{currentGrantForHistory?.title}</h4>

              {historyLoading ? (
                <div className="loading-container">
                  <div className="spinner"></div>
                </div>
              ) : applicationHistory.length === 0 ? (
                <div className="empty-state">
                  <p>No application history found for this grant.</p>
                </div>
              ) : (
                <div className="table-container">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Status</th>
                        <th>Submission Date</th>
                        <th>Notes</th>
                        <th>Created</th>
                      </tr>
                    </thead>
                    <tbody>
                      {applicationHistory
                        .slice(historyPage * historyRowsPerPage, historyPage * historyRowsPerPage + historyRowsPerPage)
                        .map((item, idx) => (
                          <tr key={idx}>
                            <td><span className="chip chip-info">{item.status}</span></td>
                            <td>{item.submission_date || 'N/A'}</td>
                            <td>{item.notes || '-'}</td>
                            <td>{item.created_at ? new Date(item.created_at).toLocaleDateString() : 'N/A'}</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={closeHistoryModal}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
