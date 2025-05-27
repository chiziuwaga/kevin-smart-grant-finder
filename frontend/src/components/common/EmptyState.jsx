import React from 'react';
import PropTypes from 'prop-types';
import { Box, Typography, Button } from '@mui/material';
import { SentimentDissatisfied as SentimentDissatisfiedIcon } from '@mui/icons-material';

function EmptyState({ 
  message, 
  icon: Icon = SentimentDissatisfiedIcon,
  action,
  actionLabel,
  onAction,
}) {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        py: 6,
        px: 2,
        textAlign: 'center',
      }}
    >
      {Icon && <Icon sx={{ fontSize: 48, mb: 2, color: 'text.secondary' }} />}
      <Typography variant="h6" color="text.secondary" gutterBottom>
        {message}
      </Typography>
      {action && onAction && (
        <Button 
          variant="outlined" 
          color="primary" 
          onClick={onAction}
          sx={{ mt: 2 }}
        >
          {actionLabel}
        </Button>
      )}
    </Box>
  );
}

EmptyState.propTypes = {
  message: PropTypes.string.isRequired,
  icon: PropTypes.elementType,
  action: PropTypes.bool,
  actionLabel: PropTypes.string,
  onAction: PropTypes.func,
};

export default EmptyState;
