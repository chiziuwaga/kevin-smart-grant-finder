import { Box, Button, Typography } from '@mui/material';
import React from 'react';
import { Link as RouterLink } from 'react-router-dom';

const NotFoundPage = () => (
  <Box sx={{ display:'flex', flexDirection:'column', alignItems:'center', mt:8 }}>
    <Typography variant="h2" gutterBottom>404</Typography>
    <Typography variant="h6" gutterBottom>Page Not Found</Typography>
    <Button component={RouterLink} to="/" variant="contained">Back to Home</Button>
  </Box>
);

export default NotFoundPage; 