import {
    Box,
    Button,
    Card,
    CardContent,
    Chip,
    Grid,
    IconButton,
    MenuItem,
    Paper,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    TextField,
    Typography,
    useTheme,
    alpha,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions
} from '@mui/material';
import {
    FilterList as FilterListIcon,
    Search as SearchIcon,
    ClearAll as ClearAllIcon,
    OpenInNew as OpenInNewIcon,
    Event as EventIcon,
    AttachMoney as AttachMoneyIcon,
} from '@mui/icons-material';
import { format, parseISO, differenceInDays } from 'date-fns';
import React, { useEffect, useState, useCallback } from 'react';
import { getGrants } from '../api/apiClient';
import { useLoading } from '../components/common/LoadingProvider';
import LoaderOverlay from '../components/common/LoaderOverlay';
import EmptyState from '../components/common/EmptyState';
import TableSkeleton from '../components/common/TableSkeleton';

const CATEGORIES = ['All', 'Research', 'Education', 'Community', 'Healthcare', 'Environment', 'Arts', 'Business', 'Energy', 'Other'];

const GrantsPage = () => {
  const theme = useTheme();
  const { startLoading, stopLoading, showError } = useLoading();
  const [loading, setLoading] = useState(false);
  const [grants, setGrants] = useState([]);
  const [selectedGrant, setSelectedGrant] = useState(null);
  const [fetchError, setFetchError] = useState(null);
  const [filters, setFilters] = useState({
    min_score: 0,
    days_to_deadline: 90,
    category: 'All'
  });

  const fetchGrants = useCallback(async () => {
    setLoading(true);
    setFetchError(null);
    startLoading();    try {
      const params = { ...filters };
      if (filters.category === 'All') delete params.category;
      
      const response = await getGrants(params);
      // Handle both paginated response format and direct array format
      const grants = response.items || response.data || response;
      
      if (Array.isArray(grants)) {
        setGrants(grants);
        if (grants.length === 0) {
          setFetchError('No grants found matching your criteria');
        }
      } else {
        console.error('Unexpected response format:', response);
        throw new Error('Invalid response format from server');
      }
    } catch (error) {
      console.error('Error fetching grants:', error);
      setFetchError(error.message || 'Failed to fetch grants. Please try again.');
      showError('An error occurred while fetching grants');
      setGrants([]);
    } finally {
      setLoading(false);
      stopLoading();
    }
  }, [filters, showError, startLoading, stopLoading]);

  useEffect(() => {
    fetchGrants();
  }, [fetchGrants]);

  const handleChange = useCallback((e) => {
    const { name, value } = e.target;
    setFilters(prev => ({ ...prev, [name]: value }));
  }, []);

  const handleApply = useCallback(() => {
    fetchGrants();
  }, [fetchGrants]);

  const handleReset = useCallback(() => {
    setFilters({
      min_score: 0,
      days_to_deadline: 90,
      category: 'All'
    });
    setFetchError(null);
    fetchGrants();
  }, [fetchGrants]);

  const handleGrantClick = useCallback((grant) => {
    setSelectedGrant(grant);
  }, []);

  const handleCloseDetail = useCallback(() => {
    setSelectedGrant(null);
  }, []);

  const getRelevanceColor = (score) => {
    if (score >= 90) return theme.palette.success.main;
    if (score >= 80) return theme.palette.info.main;
    if (score >= 70) return theme.palette.warning.main;
    return theme.palette.error.main;
  };

  return (
    <Box sx={{ p: { xs: 2, sm: 3 } }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" sx={{ 
          fontWeight: 700,
          fontSize: { xs: '1.5rem', sm: '2rem' }
        }}>
          All Grants
        </Typography>
        <Box>
          <IconButton 
            onClick={handleReset}
            sx={{ mr: 1 }}
            title="Reset filters"
          >
            <ClearAllIcon />
          </IconButton>
          <Button 
            variant="contained" 
            startIcon={<SearchIcon />}
            onClick={handleApply}
          >
            Search
          </Button>
        </Box>
      </Box>

      <Card 
        elevation={0} 
        sx={{ 
          mb: 3,
          border: 1,
          borderColor: 'divider',
        }}
      >
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <FilterListIcon sx={{ mr: 1, color: 'text.secondary' }} />
            <Typography variant="subtitle1" color="text.secondary">Filters</Typography>
          </Box>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                label="Minimum Score"
                name="min_score"
                type="number"
                fullWidth
                value={filters.min_score}
                onChange={handleChange}
                InputProps={{
                  endAdornment: '%',
                }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                label="Days to Deadline"
                name="days_to_deadline"
                type="number"
                fullWidth
                value={filters.days_to_deadline}
                onChange={handleChange}
                InputProps={{
                  endAdornment: 'days',
                }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                select
                label="Category"
                name="category"
                fullWidth
                value={filters.category}
                onChange={handleChange}
              >
                {CATEGORIES.map(opt =>
                  <MenuItem key={opt} value={opt}>{opt}</MenuItem>
                )}
              </TextField>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <LoaderOverlay loading={loading}>
        {grants.length > 0 ? (
          <>
            <TableContainer 
              component={Paper} 
              elevation={0}
              sx={{ 
                border: 1,
                borderColor: 'divider',
              }}
            >
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Title</TableCell>
                    <TableCell>Category</TableCell>
                    <TableCell>Deadline</TableCell>
                    <TableCell>Relevance</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {loading ? (
                    <TableSkeleton rows={5} columns={4} />
                  ) : (
                    grants.map(grant => {
                      const daysToDeadline = grant.deadline ? 
                        differenceInDays(parseISO(grant.deadline), new Date()) : null;
                      
                      return (
                        <TableRow 
                          key={grant.id} 
                          hover
                          onClick={() => handleGrantClick(grant)}
                          sx={{
                            '&:hover': {
                              cursor: 'pointer',
                              bgcolor: 'action.hover',
                            }
                          }}
                        >
                          <TableCell>
                            <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
                              {grant.title}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {grant.source}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Chip 
                              label={grant.category}
                              size="small"
                              sx={{
                                bgcolor: theme => theme.palette.grey[100],
                                color: theme => theme.palette.grey[800],
                              }}
                            />
                          </TableCell>
                          <TableCell>
                            {grant.deadline ? (
                              <>
                                <Typography variant="body2">
                                  {format(parseISO(grant.deadline), 'PP')}
                                </Typography>
                                <Typography 
                                  variant="caption" 
                                  color={daysToDeadline < 14 ? 'error.main' : 'text.secondary'}
                                >
                                  ({daysToDeadline} days left)
                                </Typography>
                              </>
                            ) : (
                              <Typography variant="body2" color="text.secondary">
                                N/A
                              </Typography>
                            )}
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={`${grant.relevanceScore || 0}%`}
                              size="small"
                              sx={{
                                bgcolor: alpha(getRelevanceColor(grant.relevanceScore), 0.1),
                                color: getRelevanceColor(grant.relevanceScore),
                                fontWeight: 600,
                              }}
                            />
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </TableContainer>

            <Dialog 
              open={Boolean(selectedGrant)} 
              onClose={handleCloseDetail}
              maxWidth="sm"
              fullWidth
            >
              {selectedGrant && (
                <>
                  <DialogTitle>
                    <Typography variant="h6" component="div">
                      {selectedGrant.title}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {selectedGrant.source}
                    </Typography>
                  </DialogTitle>
                  <DialogContent dividers>
                    <Box sx={{ mb: 2 }}>
                      <Chip 
                        label={selectedGrant.category}
                        size="small"
                        sx={{
                          bgcolor: theme.palette.grey[100],
                          color: theme.palette.grey[800],
                        }}
                      />
                    </Box>
                    
                    {selectedGrant.description && (
                      <Typography variant="body2" paragraph>
                        {selectedGrant.description}
                      </Typography>
                    )}

                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <EventIcon sx={{ mr: 1, color: 'text.secondary' }} />
                      <Typography variant="body2">
                        {selectedGrant.deadline ? (
                          <>
                            Deadline: {format(parseISO(selectedGrant.deadline), 'PPP')}
                            {' '}
                            <Typography 
                              component="span" 
                              variant="caption"
                              color={differenceInDays(parseISO(selectedGrant.deadline), new Date()) < 14 ? 'error.main' : 'text.secondary'}
                            >
                              ({differenceInDays(parseISO(selectedGrant.deadline), new Date())} days left)
                            </Typography>
                          </>
                        ) : 'No deadline specified'}
                      </Typography>
                    </Box>

                    {selectedGrant.fundingAmount && (
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                        <AttachMoneyIcon sx={{ mr: 1, color: 'text.secondary' }} />
                        <Typography variant="body2">
                          Funding Amount: {selectedGrant.fundingAmount}
                        </Typography>
                      </Box>
                    )}

                    <Box sx={{ mt: 2 }}>
                      <Chip
                        label={`Relevance Score: ${selectedGrant.relevanceScore || 0}%`}
                        size="small"
                        sx={{
                          bgcolor: alpha(getRelevanceColor(selectedGrant.relevanceScore), 0.1),
                          color: getRelevanceColor(selectedGrant.relevanceScore),
                          fontWeight: 600,
                        }}
                      />
                    </Box>
                  </DialogContent>
                  <DialogActions>
                    {selectedGrant.sourceUrl && (
                      <Button
                        startIcon={<OpenInNewIcon />}
                        href={selectedGrant.sourceUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        View Source
                      </Button>
                    )}
                    <Button onClick={handleCloseDetail}>
                      Close
                    </Button>
                  </DialogActions>
                </>
              )}
            </Dialog>
          </>
        ) : (          <EmptyState 
            message={fetchError || "No grants found matching your criteria"}
            action={true}
            actionLabel="Reset Filters"
            onAction={handleReset}
            error={Boolean(fetchError)}
          />
        )}
      </LoaderOverlay>
    </Box>
  );
};

export default GrantsPage;