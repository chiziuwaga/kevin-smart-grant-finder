import { useEffect, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import './LoaderOverlay.css';

function LoaderOverlay({
  loading,
  children,
  height = '300px',
  blur = false,
  message = '',
  minDisplayTime = 500
}) {
  const [shouldShow, setShouldShow] = useState(loading);
  const loadStartTime = useRef(null);

  useEffect(() => {
    if (loading) {
      loadStartTime.current = Date.now();
      setShouldShow(true);
    } else if (loadStartTime.current) {
      const elapsed = Date.now() - loadStartTime.current;
      const remaining = Math.max(0, minDisplayTime - elapsed);

      if (remaining > 0) {
        const timer = setTimeout(() => {
          setShouldShow(false);
        }, remaining);
        return () => clearTimeout(timer);
      } else {
        setShouldShow(false);
      }
    }
  }, [loading, minDisplayTime]);

  return (
    <div className="loader-overlay-container">
      {children}
      {shouldShow && (
        <div
          className={`loader-overlay ${blur ? 'loader-overlay-blur' : ''} ${shouldShow ? 'loader-overlay-visible' : ''}`}
          style={{ height }}
        >
          <div className="spinner"></div>
          {message && <div className="loader-message">{message}</div>}
        </div>
      )}
    </div>
  );
}

LoaderOverlay.propTypes = {
  loading: PropTypes.bool.isRequired,
  children: PropTypes.node.isRequired,
  height: PropTypes.string,
  blur: PropTypes.bool,
  message: PropTypes.string,
  minDisplayTime: PropTypes.number,
};

export default LoaderOverlay;
