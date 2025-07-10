import {
  PlayArrow as PlayIcon,
  Search as SearchIcon,
  CheckCircle as SuccessIcon,
  Info as InfoIcon
} from '@mui/icons-material';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  LinearProgress,
  Typography,
  Collapse,
  List,
  ListItem,
  ListItemIcon,
  ListItemText
} from '@mui/material';
import { useSnackbar } from 'notistack';
import { useState, useCallback } from 'react';

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
      <Box>
        <Button
          variant="contained"
          startIcon={isSearching ? <CircularProgress size={16} /> : <SearchIcon />}
          onClick={triggerManualSearch}
          disabled={isSearching}
          size="large"
          fullWidth
          sx={{ mb: 2 }}
        >
          {isSearching ? 'Searching for Grants...' : 'Run Grant Search'}
        </Button>
        
        {isSearching && (
          <Box sx={{ mb: 2 }}>
            <LinearProgress 
              variant="determinate" 
              value={searchProgress} 
              sx={{ mb: 1, height: 6, borderRadius: 3 }}
            />
            <Typography variant="body2" color="text.secondary" align="center">
              {currentStep}
            </Typography>
          </Box>
        )}

        {searchResults && (
          <Alert severity="success" sx={{ mb: 2 }}>
            Search completed! Found {searchResults.grants_processed || 0} grants.
          </Alert>
        )}

        {searchError && (
          <Alert 
            severity="error" 
            sx={{ mb: 2 }}
            action={
              <Button color="inherit" size="small" onClick={handleRetry}>
                Retry
              </Button>
            }
          >
            {searchError}
          </Alert>
        )}
      </Box>
    );
  }

  return (
    <Card 
      elevation={0}
      sx={{ 
        border: 1,
        borderColor: 'divider',
      }}
    >
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
          <SearchIcon sx={{ mr: 1, color: 'primary.main' }} />
          <Typography variant="h6">
            Manual Grant Discovery
          </Typography>
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Trigger a comprehensive grant search to discover new funding opportunities 
          using our AI-powered research agents.
        </Typography>

        <Button
          variant="contained"
          size="large"
          startIcon={isSearching ? <CircularProgress size={20} color="inherit" /> : <PlayIcon />}
          onClick={triggerManualSearch}
          disabled={isSearching}
          fullWidth
          sx={{ mb: 2 }}
        >
          {isSearching ? 'Discovering Grants...' : 'Start Grant Search'}
        </Button>

        <Collapse in={showDetails}>
          {isSearching && (
            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <Typography variant="body2" sx={{ flex: 1 }}>
                  Progress: {Math.round(searchProgress)}%
                </Typography>
                <Chip 
                  label="In Progress" 
                  color="primary" 
                  size="small"
                  icon={<CircularProgress size={16} />}
                />
              </Box>
              <LinearProgress 
                variant="determinate" 
                value={searchProgress} 
                sx={{ mb: 2, height: 8, borderRadius: 4 }}
              />
              <Typography variant="body2" color="text.secondary">
                {currentStep}
              </Typography>
            </Box>
          )}

          {searchResults && (
            <Alert severity="success" sx={{ mb: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                Search Completed Successfully!
              </Typography>
              <List dense>
                <ListItem disablePadding>
                  <ListItemIcon>
                    <SuccessIcon color="success" fontSize="small" />
                  </ListItemIcon>
                  <ListItemText 
                    primary={`${searchResults.grants_processed || 0} grants processed`}
                  />
                </ListItem>
                <ListItem disablePadding>
                  <ListItemIcon>
                    <InfoIcon color="info" fontSize="small" />
                  </ListItemIcon>
                  <ListItemText 
                    primary={`Status: ${searchResults.status || 'completed'}`}
                  />
                </ListItem>
              </List>
            </Alert>
          )}

          {searchError && (
            <Alert 
              severity="error" 
              sx={{ mb: 2 }}
              action={
                <Button color="inherit" size="small" onClick={handleRetry}>
                  Retry Search
                </Button>
              }
            >
              <Typography variant="subtitle2" gutterBottom>
                Search Failed
              </Typography>
              <Typography variant="body2">
                {searchError}
              </Typography>
            </Alert>
          )}
        </Collapse>

        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 2 }}>
          This will search for new grants across multiple sources and update your grant database.
          The process typically takes 20-30 seconds to complete.
        </Typography>
      </CardContent>
    </Card>
  );
};

export default ManualSearchTrigger;
