import PropTypes from 'prop-types';
import './EmptyState.css';

const MoneyBagIcon = () => (
  <svg width="48" height="48" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ opacity: 0.45 }}>
    <path d="M20 8H28L32 16H16L20 8Z" stroke="#1A1A1A" strokeWidth="2" strokeLinejoin="round"/>
    <path d="M14 16C14 16 10 24 10 32C10 40 16 44 24 44C32 44 38 40 38 32C38 24 34 16 34 16H14Z" stroke="#1A1A1A" strokeWidth="2" strokeLinejoin="round"/>
    <path d="M24 24V36M20 28H28M20 32H28" stroke="#1A1A1A" strokeWidth="2" strokeLinecap="round"/>
  </svg>
);

function EmptyState({
  title,
  subtitle,
  message,
  icon,
  action,
  actionLabel,
  onAction,
}) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">
        {icon || <MoneyBagIcon />}
      </div>
      {title && <div className="empty-state-title">{title}</div>}
      {(subtitle || message) && (
        <div className="empty-state-message">{subtitle || message}</div>
      )}
      {action && onAction && (
        <button
          className="btn btn-secondary"
          onClick={onAction}
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}

EmptyState.propTypes = {
  title: PropTypes.string,
  subtitle: PropTypes.string,
  message: PropTypes.string,
  icon: PropTypes.node,
  action: PropTypes.bool,
  actionLabel: PropTypes.string,
  onAction: PropTypes.func,
};

export default EmptyState;
