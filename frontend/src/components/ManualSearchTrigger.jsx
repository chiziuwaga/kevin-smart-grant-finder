import { useSnackbar } from 'notistack';
import { useState, useCallback } from 'react';
import './ManualSearchTrigger.css';

/**
 * Enhanced Manual Grant Search Trigger Component
 * Provides one-click grant discovery with real-time progress tracking
 */
const ManualSearchTrigger = ({ onSearchComplete, compact = false }) => {
  const { enqueueSnackbar } = useSnackbar();
  const [isSearching, setIsSearching] = useState(false);
  const [searchProgress, setSearchProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [searchError, setSearchError] = useState(null);
  const [showDetails, setShowDetails] = useState(false);

  // Simulate progressive search steps for better UX
  const simulateProgress = useCallback((onComplete) => {
    const searchSteps = [
      { label: 'Initializing search agents', duration: 2000 },
      { label: 'Discovering new grant opportunities', duration: 8000 },
      { label: 'Analyzing grant eligibility', duration: 5000 },
      { label: 'Calculating relevance scores', duration: 3000 },
      { label: 'Updating database', duration: 2000 }
    ];

    let currentProgress = 0;

    searchSteps.forEach((step, index) => {
      setTimeout(() => {
        setCurrentStep(step.label);
        const stepProgress = ((index + 1) / searchSteps.length) * 100;
        setSearchProgress(stepProgress);

        if (index === searchSteps.length - 1) {
          onComplete();
        }
      }, currentProgress);

      currentProgress += step.duration;
    });
  }, []);

  const triggerManualSearch = useCallback(async () => {
    setIsSearching(true);
    setSearchProgress(0);
    setCurrentStep('Preparing search...');
    setSearchError(null);
    setSearchResults(null);
    setShowDetails(true);

    try {
      // Start progress simulation
      simulateProgress(() => {
        setCurrentStep('Finalizing results...');
      });

      // Trigger the actual search
      const response = await fetch('/api/system/run-search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      const data = await response.json();

      if (response.ok) {
        setSearchProgress(100);
        setCurrentStep('Search completed successfully!');
        setSearchResults(data);

        enqueueSnackbar(
          `Search completed! Found ${data.grants_processed || 0} grants.`,
          { variant: 'success' }
        );

        onSearchComplete?.(data);
      } else {
        throw new Error(data.detail || 'Search failed');
      }
    } catch (error) {
      console.error('Manual search error:', error);
      setSearchError(error.message);
      setCurrentStep('Search failed');
      setSearchProgress(0);

      enqueueSnackbar(
        `Search failed: ${error.message}`,
        {
          variant: 'error',
          persist: true
        }
      );
    } finally {
      setIsSearching(false);
    }
  }, [simulateProgress, enqueueSnackbar, onSearchComplete]);

  const handleRetry = useCallback(() => {
    setSearchError(null);
    triggerManualSearch();
  }, [triggerManualSearch]);

  if (compact) {
    return (
      <div className="manual-search-compact">
        <button
          className="btn btn-primary btn-lg btn-block"
          onClick={triggerManualSearch}
          disabled={isSearching}
        >
          {isSearching ? (
            <>
              <span className="spinner spinner-sm"></span> Searching for Grants...
            </>
          ) : (
            <>
              <span className="icon">🔍</span> Run Grant Search
            </>
          )}
        </button>

        {isSearching && (
          <div className="search-progress-compact">
            <div className="progress-bar">
              <div
                className="progress-bar-fill"
                style={{ width: `${searchProgress}%` }}
              ></div>
            </div>
            <div className="search-step-text">{currentStep}</div>
          </div>
        )}

        {searchResults && (
          <div className="alert alert-success">
            Search completed! Found {searchResults.grants_processed || 0} grants.
          </div>
        )}

        {searchError && (
          <div className="alert alert-error">
            <div className="alert-content">{searchError}</div>
            <button className="btn btn-secondary btn-sm" onClick={handleRetry}>
              Retry
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="manual-search-card">
      <div className="manual-search-header">
        <span className="icon">🔍</span>
        <h3>Manual Grant Discovery</h3>
      </div>

      <p className="manual-search-description">
        Trigger a comprehensive grant search to discover new funding opportunities
        using our AI-powered research agents.
      </p>

      <button
        className="btn btn-primary btn-lg btn-block"
        onClick={triggerManualSearch}
        disabled={isSearching}
      >
        {isSearching ? (
          <>
            <span className="spinner spinner-sm"></span> Discovering Grants...
          </>
        ) : (
          <>
            <span className="icon">▶</span> Start Grant Search
          </>
        )}
      </button>

      {showDetails && (
        <div className="search-details">
          {isSearching && (
            <div className="search-progress">
              <div className="search-progress-header">
                <span>Progress: {Math.round(searchProgress)}%</span>
                <span className="badge badge-info">
                  <span className="spinner spinner-xs"></span> In Progress
                </span>
              </div>
              <div className="progress-bar progress-bar-lg">
                <div
                  className="progress-bar-fill"
                  style={{ width: `${searchProgress}%` }}
                ></div>
              </div>
              <div className="search-step-text">{currentStep}</div>
            </div>
          )}

          {searchResults && (
            <div className="alert alert-success">
              <div className="alert-title">Search Completed Successfully!</div>
              <ul className="search-results-list">
                <li>
                  <span className="icon">✓</span> {searchResults.grants_processed || 0} grants processed
                </li>
                <li>
                  <span className="icon">ℹ</span> Status: {searchResults.status || 'completed'}
                </li>
              </ul>
            </div>
          )}

          {searchError && (
            <div className="alert alert-error">
              <div className="alert-title">Search Failed</div>
              <div className="alert-content">{searchError}</div>
              <button className="btn btn-secondary btn-sm" onClick={handleRetry}>
                Retry Search
              </button>
            </div>
          )}
        </div>
      )}

      <p className="manual-search-note">
        This will search for new grants across multiple sources and update your grant database.
        The process typically takes 20-30 seconds to complete.
      </p>
    </div>
  );
};

export default ManualSearchTrigger;
