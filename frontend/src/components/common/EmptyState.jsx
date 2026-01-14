import PropTypes from 'prop-types';
import './EmptyState.css';

function EmptyState({
  message,
  icon = '😞',
  action,
  actionLabel,
  onAction,
}) {
  return (
    <div className="empty-state">
      {icon && <div className="empty-state-icon">{icon}</div>}
      <div className="empty-state-message">{message}</div>
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
  message: PropTypes.string.isRequired,
  icon: PropTypes.string,
  action: PropTypes.bool,
  actionLabel: PropTypes.string,
  onAction: PropTypes.func,
};

export default EmptyState;
