import { differenceInDays, format, parseISO } from 'date-fns';
import { useCallback, useState } from 'react';
import { createManualSearchRun, searchGrants } from '../api/apiClient';
import SearchStatusMonitor from '../components/SearchStatusMonitor';
import '../styles/swiss-theme.css';

const CATEGORIES = ['All', 'Research', 'Education', 'Community', 'Healthcare', 'Environment', 'Arts', 'Business', 'Energy', 'Other'];

const SearchPage = () => {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('All');
  const [minScore, setMinScore] = useState(70);
  const [includeExpired, setIncludeExpired] = useState(false);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [searchError, setSearchError] = useState(null);
  const [searchRunId, setSearchRunId] = useState(null);
  const [showMonitor, setShowMonitor] = useState(false);
  const [message, setMessage] = useState({ text: '', type: '' });

  const showMessage = (text, type) => {
    setMessage({ text, type });
    setTimeout(() => setMessage({ text: '', type: '' }), 3000);
  };

  const handleSearch = useCallback(async () => {
    if (!query.trim()) {
      showMessage('Please enter a search query', 'error');
      return;
    }

    setLoading(true);
    setSearchError(null);
    setHasSearched(true);
    setShowMonitor(false);

    try {
      // Create search run to track operation
      const searchRunResponse = await createManualSearchRun(
        query.trim(),
        {
          category: category === 'All' ? undefined : category,
          min_score: minScore,
          include_expired: includeExpired
        }
      );

      if (searchRunResponse && searchRunResponse.data && searchRunResponse.data.id) {
        setSearchRunId(searchRunResponse.data.id);
        setShowMonitor(true);
      }

      const body = {
        query: query.trim(),
        category: category === 'All' ? undefined : category,
        min_score: minScore
      };

      const data = await searchGrants(body);
      let resultsData = Array.isArray(data) ? data : [];

      if (!includeExpired) {
        resultsData = resultsData.filter(grant => {
          const deadline = grant.deadline || grant.deadline_date;
          if (!deadline) return true;
          return new Date(deadline) >= new Date();
        });
      }

      setResults(resultsData);

      if (resultsData.length === 0) {
        showMessage('No grants found matching your search criteria', 'info');
      } else {
        showMessage(`Found ${resultsData.length} grants`, 'success');
      }
    } catch (error) {
      console.error('Search error:', error);
      setSearchError(error.message || 'Failed to search grants');
      showMessage('Search failed. Please try again.', 'error');
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [query, category, minScore, includeExpired]);

  const handleClear = () => {
    setQuery('');
    setCategory('All');
    setMinScore(70);
    setIncludeExpired(false);
    setResults([]);
    setHasSearched(false);
    setSearchError(null);
    setSearchRunId(null);
    setShowMonitor(false);
    setMessage({ text: '', type: '' });
  };

  const getRelevanceClass = (score) => {
    if (score >= 90) return 'chip-success';
    if (score >= 80) return 'chip-info';
    if (score >= 70) return 'chip-warning';
    return 'chip-error';
  };

  return (
    <div className="container" style={{ padding: 'var(--space-3)' }}>
      <h1 className="mb-3">Search Grants</h1>

      {message.text && (
        <div className={`alert alert-${message.type} mb-3`}>
          {message.text}
        </div>
      )}

      {showMonitor && searchRunId && (
        <div className="mb-3">
          <SearchStatusMonitor searchRunId={searchRunId} />
        </div>
      )}

      <div className="card mb-4">
        <div className="form-group">
          <label className="label">Search Query *</label>
          <input
            type="text"
            className="input"
            placeholder="e.g., renewable energy, small business innovation..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          />
        </div>

        <div className="grid grid-cols-3 gap-3 mb-3">
          <div className="form-group">
            <label className="label">Category</label>
            <select
              className="input"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              {CATEGORIES.map(opt => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="label">Minimum Score: {minScore}%</label>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={minScore}
              onChange={(e) => setMinScore(parseInt(e.target.value))}
              style={{ width: '100%' }}
            />
          </div>

          <div className="form-group flex items-center">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={includeExpired}
                onChange={(e) => setIncludeExpired(e.target.checked)}
              />
              <span>Include Expired Grants</span>
            </label>
          </div>
        </div>

        <div className="flex gap-2">
          <button
            className="btn btn-primary"
            onClick={handleSearch}
            disabled={loading || !query.trim()}
          >
            {loading ? '🔍 Searching...' : '🔍 Search'}
          </button>
          <button className="btn btn-secondary" onClick={handleClear}>
            ✕ Clear
          </button>
        </div>
      </div>

      {loading && (
        <div className="loading-container">
          <div className="spinner"></div>
          <p className="mt-2">Searching grants...</p>
        </div>
      )}

      {!loading && hasSearched && results.length > 0 && (
        <div>
          <h2 className="mb-3">Search Results ({results.length})</h2>
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Category</th>
                  <th>Deadline</th>
                  <th>Relevance</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {results.map(grant => {
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
                          {grant.funder_name || 'Unknown'}
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
                      <td>
                        {grant.source_url && (
                          <a
                            href={grant.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="btn btn-sm btn-text"
                          >
                            View ↗
                          </a>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!loading && hasSearched && results.length === 0 && (
        <div className="empty-state">
          <div style={{ fontSize: '3rem', marginBottom: 'var(--space-2)' }}>🔍</div>
          <p>{searchError || 'No grants found matching your search'}</p>
          <p className="text-secondary text-sm">Try adjusting your search criteria</p>
        </div>
      )}
    </div>
  );
};

export default SearchPage;
