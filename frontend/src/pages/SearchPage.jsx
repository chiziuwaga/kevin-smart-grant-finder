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
    Slider,
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
} from '@mui/material';
import {
    Search as SearchIcon,
    Clear as ClearIcon,
} from '@mui/icons-material';
import { format, parseISO, differenceInDays } from 'date-fns';
import React, { useState, useCallback } from 'react';
import { searchGrants } from '../api/apiClient';
import { useLoading } from '../components/common/LoadingProvider';
import LoaderOverlay from '../components/common/LoaderOverlay';
import EmptyState from '../components/common/EmptyState';
import TableSkeleton from '../components/common/TableSkeleton';

const CATEGORIES = ['All', 'Research', 'Education', 'Community', 'Healthcare', 'Environment', 'Arts', 'Business', 'Energy', 'Other'];

const SearchPage = () => {
  const theme = useTheme();
  const { startLoading, stopLoading, showError } = useLoading();
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('All');
  const [minScore, setMinScore] = useState(70);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [searchError, setSearchError] = useState(null);

  const handleSearch = useCallback(async () => {
    if (!query.trim()) {
      showError('Please enter a search query');
      return;
    }

    setLoading(true);
    setSearchError(null);
    setHasSearched(true);
    startLoading();

    try {
      const body = { 
        query: query.trim(), 
        category: category === 'All' ? undefined : category, 
        min_score: minScore 
      };
      const data = await searchGrants(body);
      setResults(Array.isArray(data) ? data : []);
      
      if (Array.isArray(data) && data.length === 0) {
        setSearchError('No grants found matching your criteria');
      }
    } catch (error) {
      console.error('Search error:', error);
      setSearchError(error.message || 'Failed to search grants. Please try again.');
      showError('An error occurred while searching. Please try again.');
      setResults([]);
    } finally {
      setLoading(false);
      stopLoading();
    }
  }, [query, category, minScore, showError, startLoading, stopLoading]);

  const handleReset = useCallback(() => {
    setQuery('');
    setCategory('All');
    setMinScore(70);
    setResults([]);
    setHasSearched(false);
    setSearchError(null);
  }, []);

  const handleKeyPress = useCallback((e) => {
    if (e.key === 'Enter' && query.trim()) {
      handleSearch();
    }
  }, [query, handleSearch]);

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
          Search Grants
        </Typography>
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
          <Grid container spacing={2} alignItems="flex-start">
            <Grid item xs={12} md={5}>
              <TextField 
                label="Search grants..."
                fullWidth
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Enter keywords, categories, or specific criteria"
                InputProps={{
                  endAdornment: query && (
                    <IconButton
                      size="small"
                      onClick={() => setQuery('')}
                      edge="end"
                    >
                      <ClearIcon fontSize="small" />
                    </IconButton>
                  ),
                }}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField 
                select
                label="Category"
                fullWidth
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                {CATEGORIES.map(opt =>
                  <MenuItem key={opt} value={opt}>{opt}</MenuItem>
                )}
              </TextField>
            </Grid>
            <Grid item xs={12} md={2}>
              <Typography variant="subtitle2" gutterBottom>
                Minimum Relevance
              </Typography>
              <Box sx={{ px: 1 }}>
                <Slider
                  value={minScore}
                  onChange={(e, val) => setMinScore(val)}
                  valueLabelDisplay="auto"
                  min={0}
                  max={100}
                  marks={[
                    { value: 0, label: '0%' },
                    { value: 50, label: '50%' },
                    { value: 100, label: '100%' },
                  ]}
                />
              </Box>
            </Grid>
            <Grid item xs={12} md={2} sx={{ display: 'flex', alignItems: 'flex-end' }}>
              <Button
                variant="contained"
                onClick={handleSearch}
                fullWidth
                disabled={!query.trim()}
                startIcon={<SearchIcon />}
                sx={{ height: 56 }}
              >
                Search
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <LoaderOverlay loading={loading}>
        {hasSearched ? (
          results.length > 0 ? (
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
                    results.map(grant => {
                      const daysToDeadline = grant.deadline ? 
                        differenceInDays(parseISO(grant.deadline), new Date()) : null;

                      return (
                        <TableRow 
                          key={grant.id} 
                          hover
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
          ) : (
            <EmptyState 
              message={searchError || "No grants found matching your search criteria"}
              action={true}
              actionLabel="Reset Search"
              onAction={handleReset}
            />
          )
        ) : (
          <Box 
            sx={{ 
              textAlign: 'center',
              py: 8,
              px: 2,
            }}
          >
            <Typography variant="h6" color="text.secondary" gutterBottom>
              Enter your search criteria above to find grants
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Try searching by keywords, categories, or specific requirements
            </Typography>
            {searchError && (
              <Typography 
                variant="body2" 
                color="error" 
                sx={{ mt: 2, fontWeight: 500 }}
              >
                {searchError}
              </Typography>
            )}
          </Box>
        )}
      </LoaderOverlay>
    </Box>
  );
};

export default SearchPage;