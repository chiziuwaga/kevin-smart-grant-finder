import { differenceInDays, format, parseISO } from 'date-fns';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './styles/GrantDetailsModal.css';

const GrantDetailsModal = ({ grant, open, onClose }) => {
  if (!grant || !open) return null;

  const daysToDeadline =
    grant.deadline || grant.deadline_date
      ? differenceInDays(
          parseISO(grant.deadline || grant.deadline_date),
          new Date()
        )
      : null;

  const isExpired = daysToDeadline !== null && daysToDeadline < 0;
  const isUrgent =
    daysToDeadline !== null && daysToDeadline > 0 && daysToDeadline < 14;

  const renderScoreSection = (scores, title) => {
    if (
      !scores ||
      typeof scores !== 'object' ||
      Object.keys(scores).length === 0
    ) {
      return null;
    }

    return (
      <div className="score-section">
        <h3>{title}</h3>
        <div className="score-grid">
          {Object.entries(scores).map(([key, value]) => (
            <div className="score-item" key={key}>
              <div className="score-label">
                {key
                  .replace(/_/g, ' ')
                  .replace(/\b\w/g, (c) => c.toUpperCase())}
              </div>
              <div className="score-value">
                {typeof value === 'number' ? value.toFixed(2) : value}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-content modal-content-large"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <div className="grant-title-section">
            <h2>{grant.title}</h2>
            <div className="grant-badges">
              {isExpired && <span className="badge badge-error">EXPIRED</span>}
              {isUrgent && (
                <span className="badge badge-warning">
                  {daysToDeadline} days left
                </span>
              )}
              <span className="badge badge-primary">
                {grant.category || grant.identified_sector || 'Other'}
              </span>
            </div>
          </div>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <div className="modal-body grant-details-body">
          <div className="grant-details-layout">
            {/* Main Content */}
            <div className="grant-main-content">
              <section className="grant-section">
                <h3>Description</h3>
                <p>{grant.description || 'No description available'}</p>
              </section>

              {grant.summary_llm && (
                <section className="grant-section">
                  <h3>AI-Generated Summary</h3>
                  <div className="ai-summary markdown-content">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {grant.summary_llm}
                    </ReactMarkdown>
                  </div>
                </section>
              )}

              {grant.eligibility_summary_llm && (
                <section className="grant-section">
                  <h3>Eligibility Requirements</h3>
                  <div className="eligibility-box markdown-content">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {grant.eligibility_summary_llm}
                    </ReactMarkdown>
                  </div>
                </section>
              )}
            </div>

            {/* Sidebar with Key Details */}
            <aside className="grant-sidebar">
              <div className="sidebar-card">
                <h3>Key Details</h3>

                {grant.funder_name && (
                  <div className="detail-item">
                    <div className="detail-label">Funder</div>
                    <div className="detail-value">{grant.funder_name}</div>
                  </div>
                )}

                <div className="detail-item">
                  <div className="detail-label">Funding</div>
                  <div className="detail-value">
                    {grant.funding_amount_display ||
                      grant.fundingAmount ||
                      'Not specified'}
                  </div>
                </div>

                <div className="detail-item">
                  <div className="detail-label">Deadline</div>
                  <div
                    className={`detail-value ${
                      isExpired
                        ? 'text-error'
                        : isUrgent
                        ? 'text-warning'
                        : ''
                    }`}
                  >
                    {grant.deadline || grant.deadline_date
                      ? format(
                          parseISO(grant.deadline || grant.deadline_date),
                          'MMM d, yyyy'
                        )
                      : 'Not specified'}
                  </div>
                  {daysToDeadline !== null && (
                    <div className="detail-subtext">
                      {isExpired
                        ? 'Expired'
                        : `${daysToDeadline} days remaining`}
                    </div>
                  )}
                </div>

                {grant.geographic_scope && (
                  <div className="detail-item">
                    <div className="detail-label">Geographic Scope</div>
                    <div className="detail-value">{grant.geographic_scope}</div>
                  </div>
                )}

                <div className="detail-item">
                  <div className="detail-label">Source</div>
                  <div className="detail-value">
                    {grant.source_name || grant.source || 'Unknown'}
                  </div>
                </div>

                {grant.overall_composite_score !== null &&
                  grant.overall_composite_score !== undefined && (
                    <div className="score-highlight">
                      <div className="score-highlight-label">
                        Overall Relevance Score
                      </div>
                      <div className="score-highlight-value">
                        {grant.overall_composite_score.toFixed(1)}
                      </div>
                    </div>
                  )}
              </div>
            </aside>
          </div>

          {/* Keywords */}
          {grant.keywords && grant.keywords.length > 0 && (
            <section className="grant-section">
              <h3>Keywords</h3>
              <div className="keywords-list">
                {grant.keywords.map((keyword, idx) => (
                  <span key={idx} className="keyword-chip">
                    {keyword}
                  </span>
                ))}
              </div>
            </section>
          )}

          {/* Detailed Scores */}
          <div className="scores-container">
            {renderScoreSection(grant.research_scores, 'Research Scores')}
            {renderScoreSection(grant.compliance_scores, 'Compliance Scores')}
          </div>

          {/* Enrichment Log */}
          {grant.enrichment_log && grant.enrichment_log.length > 0 && (
            <section className="grant-section">
              <h3>Processing Log</h3>
              <ul className="log-list">
                {grant.enrichment_log.map((log, idx) => (
                  <li key={idx}>{log}</li>
                ))}
              </ul>
            </section>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
          {(grant.source_url || grant.sourceUrl) && (
            <a
              className="btn btn-primary"
              href={grant.source_url || grant.sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
            >
              View Original Grant →
            </a>
          )}
        </div>
      </div>
    </div>
  );
};

export default GrantDetailsModal;
