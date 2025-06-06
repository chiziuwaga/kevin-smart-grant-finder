import React from 'react';
import PropTypes from 'prop-types';
import { Box, CircularProgress, Typography, Fade } from '@mui/material';

function LoaderOverlay({ 
  loading, 
  children, 
  height = '300px', 
  blur = false,
  message = '',
  minDisplayTime = 500
}) {
  const [shouldShow, setShouldShow] = React.useState(loading);
  const loadStartTime = React.useRef(null);

  React.useEffect(() => {
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
    <Box sx={{ position: 'relative' }}>
      {children}
      <Fade in={shouldShow} timeout={300}>
        <Box
          sx={{
            position: 'absolute',
            inset: 0,
            bgcolor: blur ? 'rgba(255,255,255,0.8)' : 'rgba(255,255,255,0.6)',
            backdropFilter: blur ? 'blur(4px)' : 'none',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 2,
            height,
            zIndex: (theme) => theme.zIndex.drawer + 1,
            transition: (theme) =>
              theme.transitions.create(['backdrop-filter', 'background-color'], {
                duration: theme.transitions.duration.standard,
              }),
          }}
        >
          <CircularProgress size={40} />
          {message && (
            <Typography 
              variant="body2" 
              color="text.secondary"
              sx={{ mt: 1 }}
            >
              {message}
            </Typography>
          )}
        </Box>
      </Fade>
    </Box>
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
