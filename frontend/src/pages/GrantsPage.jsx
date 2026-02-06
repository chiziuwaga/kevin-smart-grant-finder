import { differenceInDays, format, parseISO } from 'date-fns';
import { useCallback, useEffect, useState } from 'react';
import { getGrants } from '../api/apiClient';
import EmptyState from '../components/common/EmptyState';
import '../styles/swiss-theme.css';

const CATEGORIES = ['All', 'Research', 'Education', 'Community', 'Healthcare', 'Environment', 'Arts', 'Business', 'Energy', 'Other'];

const GrantsPage = () => {
  const [loading, setLoading] = useState(false);
  const [grants, setGrants] = useState([]);
  const [selectedGrant, setSelectedGrant] = useState(null);
  const [fetchError, setFetchError] = useState(null);
  const [message, setMessage] = useState({ text: '', type: '' });

  const [filters, setFilters] = useState({
    min_score: 0,
    days_to_deadline: 90,
    category: 'All',
    includeExpired: false
  });

  const showMessage = (text, type) => {
    setMessage({ text, type });
    setTimeout(() => setMessage({ text: '', type: '' }), 3000);
  };

  const fetchGrants = useCallback(async () => {
    setLoading(true);
    setFetchError(null);

    try {
      const params = { ...filters };
      if (filters.category === 'All') delete params.category;

      const response = await getGrants(params);
      let grantsData = response.items || response.data || response;

      if (!filters.includeExpired) {
        grantsData = grantsData.filter(grant => {
          const deadline = grant.deadline || grant.deadline_date;
          if (!deadline) return true;
          return new Date(deadline) >= new Date();
        });
      }

      if (Array.isArray(grantsData)) {
        setGrants(grantsData);
        if (grantsData.length === 0) {
          setFetchError('No grants found matching your criteria');
        }
      } else {
        console.error('Unexpected response format:', response);
        throw new Error('Invalid response format from server');
      }
    } catch (error) {
      console.error('Error fetching grants:', error);
      setFetchError(error.message || 'Failed to fetch grants. Please try again.');
      showMessage('An error occurred while fetching grants', 'error');
      setGrants([]);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchGrants();
  }, [fetchGrants]);

  const handleChange = useCallback((e) => {
    const { name, value, type, checked } = e.target;
    setFilters(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  }, []);

  const handleApply = useCallback(() => {
    fetchGrants();
  }, [fetchGrants]);

  const handleReset = useCallback(() => {
    setFilters({
      min_score: 0,
      days_to_deadline: 90,
      category: 'All',
      includeExpired: false
    });
    setFetchError(null);
  }, []);

  const handleGrantClick = useCallback((grant) => {
    setSelectedGrant(grant);
  }, []);

  const handleCloseDetail = useCallback(() => {
    setSelectedGrant(null);
  }, []);

  const getRelevanceClass = (score) => {
    if (score >= 90) return 'chip-success';
    if (score >= 80) return 'chip-info';
    if (score >= 70) return 'chip-warning';
    return 'chip-error';
  };

  return (
    <div className="container" style={{ padding: 'var(--space-3)' }}>
      <div className="flex justify-between items-center mb-3">
        <h1>All Grants</h1>
        <div className="flex gap-2">
          <button className="btn btn-text" onClick={handleReset} title="Reset filters">
            ↺ Reset
          </button>
          <button className="btn btn-primary" onClick={handleApply}>
            🔍 Search
          </button>
        </div>
      </div>

      {message.text && (
        <div className={`alert alert-${message.type} mb-3`}>
          {message.text}
        </div>
      )}

      <div className="card mb-3">
        <div className="flex items-center mb-2">
          <span style={{ marginRight: 'var(--space-1)' }}>🔍</span>
          <h3 className="text-secondary text-sm" style={{ margin: 0 }}>FILTERS</h3>
        </div>
        <div className="grid grid-cols-4" style={{ gap: 'var(--space-2)', alignItems: 'end' }}>
          <div className="form-group">
            <label className="label">Minimum Score</label>
            <input
              type="number"
              name="min_score"
              className="input"
              value={filters.min_score}
              onChange={handleChange}
              min="0"
              max="100"
            />
          </div>
          <div className="form-group">
            <label className="label">Days to Deadline</label>
            <input
              type="number"
              name="days_to_deadline"
              className="input"
              value={filters.days_to_deadline}
              onChange={handleChange}
              min="0"
            />
          </div>
          <div className="form-group">
            <label className="label">Category</label>
            <select
              name="category"
              className="input"
              value={filters.category}
              onChange={handleChange}
            >
              {CATEGORIES.map(opt => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                name="includeExpired"
                checked={filters.includeExpired}
                onChange={handleChange}
              />
              <span>Include Expired</span>
            </label>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="loading-container">
          <div className="spinner"></div>
          <p className="mt-2">Loading grants...</p>
        </div>
      ) : grants.length > 0 ? (
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Category</th>
                <th>Deadline</th>
                <th>Relevance</th>
              </tr>
            </thead>
            <tbody>
              {grants.map(grant => {
                const daysToDeadline = grant.deadline ?
                  differenceInDays(parseISO(grant.deadline), new Date()) : null;
                const isUrgent = daysToDeadline !== null && daysToDeadline < 14 && daysToDeadline >= 0;
                const isExpired = daysToDeadline !== null && daysToDeadline < 0;

                return (
                  <tr
                    key={grant.id}
                    onClick={() => handleGrantClick(grant)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td>
                      <div style={{ fontWeight: '600', marginBottom: '4px' }}>
                        {grant.title}
                      </div>
                      <div className="text-xs text-secondary">
                        {grant.source || grant.funder_name || 'Unknown'}
                      </div>
                    </td>
                    <td>
                      <span className="chip">
                        {grant.category || grant.identified_sector || 'Other'}
                      </span>
                    </td>
                    <td>
                      {grant.deadline ? (
                        <div>
                          <div style={{ marginBottom: '4px' }}>
                            {format(parseISO(grant.deadline), 'PP')}
                          </div>
                          <div
                            className="text-xs"
                            style={{
                              color: isExpired ? '#E53935' : isUrgent ? '#E53935' : 'var(--color-gray-600)'
                            }}
                          >
                            {isExpired ? 'Expired' : `${daysToDeadline} days left`}
                          </div>
                        </div>
                      ) : (
                        <span className="text-secondary">N/A</span>
                      )}
                    </td>
                    <td>
                      <span className={`chip ${getRelevanceClass(grant.overall_composite_score || grant.relevanceScore || 0)}`}>
                        {(grant.overall_composite_score || grant.relevanceScore || 0).toFixed(0)}%
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState
          title="No grants found yet"
          subtitle={fetchError || "Your money finder hasn't discovered grants matching these filters. Try adjusting your criteria or run a new search."}
          action={true}
          actionLabel="Reset Filters"
          onAction={handleReset}
        />
      )}

      {/* Grant Detail Modal */}
      {selectedGrant && (
        <div className="modal-backdrop" onClick={handleCloseDetail}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '700px' }}>
            <div className="modal-header">
              <h3 className="modal-title">{selectedGrant.title}</h3>
              <button className="modal-close" onClick={handleCloseDetail}>✕</button>
            </div>
            <div className="modal-body">
              <div style={{ marginBottom: 'var(--space-2)' }}>
                <strong>Funder:</strong> {selectedGrant.funder_name || 'Unknown'}
              </div>
              <div style={{ marginBottom: 'var(--space-2)' }}>
                <strong>Category:</strong> <span className="chip">{selectedGrant.category || 'Other'}</span>
              </div>
              {selectedGrant.deadline && (
                <div style={{ marginBottom: 'var(--space-2)' }}>
                  <strong>Deadline:</strong> {format(parseISO(selectedGrant.deadline), 'PPP')}
                </div>
              )}
              <div style={{ marginBottom: 'var(--space-2)' }}>
                <strong>Description:</strong>
                <p style={{ marginTop: 'var(--space-1)' }}>{selectedGrant.description || 'No description available'}</p>
              </div>
              {selectedGrant.source_url && (
                <div>
                  <a href={selectedGrant.source_url} target="_blank" rel="noopener noreferrer" className="btn btn-text">
                    View Source ↗
                  </a>
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={handleCloseDetail}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default GrantsPage;
