import { differenceInDays, format, parseISO } from 'date-fns';
import { useState } from 'react';
import './GrantCard.css';

const GrantCard = ({
  grant,
  onSave,
  isSaved,
  onViewDetails,
  onSelect,
  isSelected,
}) => {
  const [showScoreTooltip, setShowScoreTooltip] = useState(false);

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

  const getScoreColor = (score) => {
    if (score >= 90) return 'var(--color-success)';
    if (score >= 80) return 'var(--color-accent-blue)';
    if (score >= 70) return 'var(--color-warning)';
    return 'var(--color-error)';
  };

  const formatScoreValue = (value) => {
    if (typeof value === 'number') {
      return value.toFixed(2);
    }
    if (typeof value === 'string' && !isNaN(parseFloat(value))) {
      return parseFloat(value).toFixed(2);
    }
    return value;
  };

  const renderScores = (scores, title) => {
    if (!scores || typeof scores !== 'object' || Object.keys(scores).length === 0) {
      return null;
    }

    return (
      <div className="score-section">
        <div className="score-title">{title}:</div>
        {Object.entries(scores).map(([key, value]) => (
          <div key={key} className="score-item">
            {key.replace(/_/g, ' ').replace(/\b(\w)/g, (c) => c.toUpperCase())}: {formatScoreValue(value)}
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className={`grant-card ${isSelected ? 'grant-card-selected' : ''}`}>
      <div className="grant-card-header">
        <div className="grant-card-badges">
          <span className="badge badge-category">
            {grant.category || grant.identified_sector || 'Other'}
          </span>
          {isExpired && <span className="badge badge-error">EXPIRED</span>}
          {isUrgent && <span className="badge badge-warning">{daysToDeadline} days left</span>}
        </div>

        {onSelect && (
          <input
            type="checkbox"
            className="grant-card-checkbox"
            checked={isSelected || false}
            onChange={(e) => onSelect(grant.id, e.target.checked)}
          />
        )}

        <div
          className="grant-card-score"
          style={{
            borderColor: getScoreColor(grant.overall_composite_score || 0),
          }}
        >
          {grant.overall_composite_score !== undefined && grant.overall_composite_score !== null
            ? grant.overall_composite_score.toFixed(0)
            : grant.relevanceScore !== undefined && grant.relevanceScore !== null
            ? grant.relevanceScore.toString()
            : 'N/A'}
        </div>
      </div>

      <h3 className="grant-card-title">{grant.title}</h3>

      {grant.funder_name && (
        <div className="grant-card-funder">Funder: {grant.funder_name}</div>
      )}

      <div className="grant-card-source">
        {grant.source_name || grant.source || 'Unknown Source'}
      </div>

      {grant.description && (
        <p className="grant-card-description">
          {grant.description.length > 140
            ? `${grant.description.substring(0, 140)}...`
            : grant.description}
        </p>
      )}

      {grant.summary_llm && (
        <div className="grant-card-summary">
          <div className="grant-card-summary-label">AI Summary:</div>
          <div className="grant-card-summary-text">
            {grant.summary_llm.length > 120
              ? `${grant.summary_llm.substring(0, 120)}...`
              : grant.summary_llm}
          </div>
        </div>
      )}

      {grant.eligibility_summary_llm && (
        <div className="grant-card-summary">
          <div className="grant-card-summary-label">AI Eligibility:</div>
          <div className="grant-card-summary-text">
            {grant.eligibility_summary_llm.length > 120
              ? `${grant.eligibility_summary_llm.substring(0, 120)}...`
              : grant.eligibility_summary_llm}
          </div>
        </div>
      )}

      <div className="grant-card-details">
        {(grant.research_scores || grant.compliance_scores) && (
          <div className="grant-card-scores-button-container">
            <button
              className="btn btn-text grant-card-scores-button"
              onMouseEnter={() => setShowScoreTooltip(true)}
              onMouseLeave={() => setShowScoreTooltip(false)}
            >
              <span className="icon">ℹ</span> View Detailed Scores
            </button>
            {showScoreTooltip && (
              <div className="grant-card-scores-tooltip">
                {renderScores(grant.research_scores, 'Research Scores')}
                {renderScores(grant.compliance_scores, 'Compliance Scores')}
              </div>
            )}
          </div>
        )}

        <div className="grant-card-info">
          <span className="icon icon-time">⏰</span>
          <span>
            Deadline:{' '}
            {grant.deadline || grant.deadline_date
              ? format(parseISO(grant.deadline || grant.deadline_date), 'MMM d, yyyy')
              : 'Not specified'}
            {daysToDeadline !== null && (
              <span
                className={`grant-card-deadline-days ${
                  isExpired ? 'expired' : isUrgent ? 'urgent' : ''
                }`}
              >
                {' '}({isExpired ? 'Expired' : `${daysToDeadline} days`})
              </span>
            )}
          </span>
        </div>

        <div className="grant-card-info">
          <span className="icon icon-money">💰</span>
          <span>
            Funding: {grant.funding_amount_display || grant.fundingAmount || 'Not specified'}
          </span>
        </div>

        {grant.geographic_scope && (
          <div className="grant-card-info">
            <strong>Geographic Scope:</strong> {grant.geographic_scope}
          </div>
        )}

        {grant.keywords && grant.keywords.length > 0 && (
          <div className="grant-card-keywords">
            <div className="grant-card-keywords-label">Keywords:</div>
            <div className="grant-card-keywords-list">
              {grant.keywords.slice(0, 3).map((keyword, idx) => (
                <span key={idx} className="keyword-tag">
                  {keyword}
                </span>
              ))}
              {grant.keywords.length > 3 && (
                <span className="keywords-more">+{grant.keywords.length - 3} more</span>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="grant-card-actions">
        <button
          className="btn btn-secondary btn-sm"
          onClick={() => onViewDetails && onViewDetails(grant)}
        >
          Full Details
        </button>

        <a
          className="btn btn-primary btn-sm"
          href={grant.source_url || grant.sourceUrl}
          target="_blank"
          rel="noopener noreferrer"
        >
          View Application <span className="icon">↗</span>
        </a>

        <button
          className={`btn-icon ${isSaved ? 'btn-icon-active' : ''}`}
          onClick={() => onSave && onSave(grant.id, !isSaved)}
          aria-label={isSaved ? 'Remove bookmark' : 'Add bookmark'}
        >
          {isSaved ? '★' : '☆'}
        </button>
      </div>
    </div>
  );
};

export default GrantCard;
