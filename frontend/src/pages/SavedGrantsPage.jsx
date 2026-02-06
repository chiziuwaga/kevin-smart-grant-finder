import { format, parseISO, differenceInDays } from 'date-fns';
import React, { useEffect, useState, useCallback } from 'react';
import { getSavedGrants, unsaveGrant } from '../api/apiClient';
import '../styles/swiss-theme.css';

const SavedGrantsPage = () => {
  const [loading, setLoading] = useState(true);
  const [grants, setGrants] = useState([]);
  const [message, setMessage] = useState({ text: '', type: '' });

  const showMessage = (text, type) => {
    setMessage({ text, type });
    setTimeout(() => setMessage({ text: '', type: '' }), 3000);
  };

  const fetchSaved = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getSavedGrants();
      setGrants(data.items || data);
    } catch(e) {
      console.error(e);
      showMessage('Failed to fetch saved grants', 'error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSaved();
  }, [fetchSaved]);

  const handleUnsave = async (id) => {
    try {
      await unsaveGrant(id);
      setGrants(prev => prev.filter(g => g.id !== id));
      showMessage('Grant removed from saved items', 'success');
    } catch(e) {
      console.error(e);
      showMessage('Failed to remove grant', 'error');
    }
  };

  const getRelevanceColor = (score) => {
    if (score >= 90) return '#43A047';
    if (score >= 80) return '#1976D2';
    if (score >= 70) return '#FDD835';
    return '#E53935';
  };

  const getRelevanceClass = (score) => {
    if (score >= 90) return 'chip-success';
    if (score >= 80) return 'chip-info';
    if (score >= 70) return 'chip-warning';
    return 'chip-error';
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p className="mt-2">Loading saved grants...</p>
      </div>
    );
  }

  return (
    <div className="container" style={{ padding: 'var(--space-3)' }}>
      <div className="flex items-center mb-3">
        <span style={{ fontSize: '2rem', marginRight: 'var(--space-2)' }}>🔖</span>
        <h1>Saved Grants</h1>
      </div>

      {message.text && (
        <div className={`alert alert-${message.type} mb-3`}>
          {message.text}
        </div>
      )}

      {grants.length > 0 ? (
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Category</th>
                <th>Deadline</th>
                <th>Relevance</th>
                <th style={{ textAlign: 'center' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {grants.map(grant => {
                const daysToDeadline = grant.deadline ?
                  differenceInDays(parseISO(grant.deadline), new Date()) : null;
                const isUrgent = daysToDeadline !== null && daysToDeadline < 14 && daysToDeadline >= 0;
                const isExpired = daysToDeadline !== null && daysToDeadline < 0;

                return (
                  <tr key={grant.id}>
                    <td>
                      <div style={{ fontWeight: '600', marginBottom: '4px' }}>
                        {grant.title}
                      </div>
                      <div className="text-xs text-secondary">
                        {grant.source || grant.funder_name || 'Unknown source'}
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
                      <span
                        className={`chip ${getRelevanceClass(grant.relevanceScore || grant.overall_composite_score || 0)}`}
                      >
                        {grant.relevanceScore || grant.overall_composite_score || 0}%
                      </span>
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <button
                        className="btn btn-sm btn-text"
                        onClick={() => handleUnsave(grant.id)}
                        title="Remove from saved"
                        style={{ color: '#E53935' }}
                      >
                        🗑️ Remove
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">
          <div style={{ fontSize: '3rem', marginBottom: 'var(--space-2)' }}>🔖</div>
          <p>No saved grants yet</p>
          <p className="text-secondary text-sm">
            Save grants from the dashboard to see them here
          </p>
        </div>
      )}
    </div>
  );
};

export default SavedGrantsPage;
