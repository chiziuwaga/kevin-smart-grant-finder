import React, { useState, useEffect, useCallback } from 'react';
import { 
  Container, 
  Grid, 
  CircularProgress, 
  Typography, 
  Alert,
  Box,
  Paper,
  Button,
  TextField,
  Select,
  MenuItem,
  InputLabel,
  FormControl,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination
} from '@mui/material';
import { Refresh as RefreshIcon, AddComment as AddCommentIcon, Visibility as VisibilityIcon } from '@mui/icons-material';
import GrantCard from './GrantCard';
import apiClient from '../api/apiClient'; // apiClient will be the compiled JS version of apiClient.ts
// Types are for JSDoc and understanding, not enforced by JS runtime directly
/**
 * @typedef {import('../api/types').EnrichedGrant} EnrichedGrant
 * @typedef {import('../api/types').ApplicationFeedbackData} ApplicationFeedbackData
 * @typedef {import('../api/types').ApplicationHistory} ApplicationHistory
 * @typedef {import('../api/types').GrantSearchFilters} GrantSearchFilters
 */

const Dashboard = () => {
  const [grants, setGrants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [savedGrants, setSavedGrants] = useState(new Set());
  const [filters, setFilters] = useState({ 
    searchText: '', 
    category: '', 
    minOverallScore: '', // New filter for minimum overall_composite_score
    maxOverallScore: ''  // New filter for maximum overall_composite_score
  });
  // Add state for Application Feedback Modal
  const [feedbackModalOpen, setFeedbackModalOpen] = useState(false);
  const [currentGrantForFeedback, setCurrentGrantForFeedback] = useState(null);
  const [feedbackData, setFeedbackData] = useState({});
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  const [feedbackError, setFeedbackError] = useState(null);

  // Add state for Application History
  const [applicationHistory, setApplicationHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState(null);
  const [historyModalOpen, setHistoryModalOpen] = useState(false);
  const [currentGrantForHistory, setCurrentGrantForHistory] = useState(null);
  const [historyPage, setHistoryPage] = useState(0);
  const [historyRowsPerPage, setHistoryRowsPerPage] = useState(5);

  const fetchGrants = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Use searchText and category from filters state
      const { searchText, category, minOverallScore, maxOverallScore, ...otherFilters } = filters;
      const params = { 
        searchText: searchText || undefined,
        category: category || undefined,
        min_overall_score: minOverallScore ? parseFloat(minOverallScore) : undefined, // Pass to backend
        max_overall_score: maxOverallScore ? parseFloat(maxOverallScore) : undefined, // Pass to backend
        ...otherFilters 
      };
      const response = await apiClient.getGrants(params);
      setGrants(response.items);
    } catch (err) {
      setError(err.message || 'Failed to fetch grants');
    }
    setLoading(false);
  }, [filters]); // Dependency is now just filters

  useEffect(() => {
    fetchGrants();
  }, [fetchGrants]);

  useEffect(() => {
    const fetchSaved = async () => {
      try {
        const response = await apiClient.getSavedGrants();
        setSavedGrants(new Set(response.items.map(g => g.id)));
      } catch (err) {
        console.error('Failed to fetch saved grants:', err);
      }
    };
    fetchSaved();
  }, []);

  const handleSaveGrant = async (grantId, save) => {
    try {
      if (save) {
        await apiClient.saveGrant(grantId);
        setSavedGrants(prev => new Set(prev).add(grantId));
      } else {
        await apiClient.unsaveGrant(grantId);
        setSavedGrants(prev => {
          const next = new Set(prev);
          next.delete(grantId);
          return next;
        });
      }
    } catch (err) {
      console.error(`Failed to ${save ? 'save' : 'unsave'} grant:`, err);
      setError(`Failed to ${save ? 'save' : 'unsave'} grant. Please try again.`);
    }
  };

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters(prev => ({ ...prev, [name]: value }));
  };

  const handleSearch = () => {
    fetchGrants();
  };

  // Application Feedback Modal Handlers
  const openFeedbackModal = (grant) => {
    setCurrentGrantForFeedback(grant);
    setFeedbackData({ grant_id: grant.id });
    setFeedbackError(null);
    setFeedbackModalOpen(true);
  };

  const closeFeedbackModal = () => {
    setFeedbackModalOpen(false);
    setCurrentGrantForFeedback(null);
    setFeedbackData({});
  };

  const handleFeedbackChange = (e) => {
    const { name, value } = e.target;
    setFeedbackData(prev => ({ ...prev, [name]: value }));
  };

  const handleFeedbackSubmit = async () => {
    if (!currentGrantForFeedback || !feedbackData.grant_id || !feedbackData.status || !feedbackData.submission_date) {
      setFeedbackError('Please fill in all required fields (status, submission date).');
      return;
    }
    setFeedbackSubmitting(true);
    setFeedbackError(null);
    try {
      await apiClient.submitApplicationFeedback(feedbackData);
      closeFeedbackModal();
      alert('Feedback submitted successfully!');
      // Optionally, refresh history if the current grant's history was open
      if (currentGrantForHistory && currentGrantForHistory.id === feedbackData.grant_id) {
        fetchApplicationHistory(feedbackData.grant_id);
      }
    } catch (err) {
      setFeedbackError(err.message || 'Failed to submit feedback.');
    }
    setFeedbackSubmitting(false);
  };

  // Application History Modal Handlers
  const fetchApplicationHistory = async (grantId) => {
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const response = await apiClient.getApplicationHistoryForGrant(grantId);
      setApplicationHistory(response.items);
    } catch (err) {
      setHistoryError(err.message || 'Failed to fetch application history.');
      setApplicationHistory([]); // Clear history on error
    }
    setHistoryLoading(false);
  };

  const openHistoryModal = (grant) => {
    setCurrentGrantForHistory(grant);
    fetchApplicationHistory(grant.id);
    setHistoryModalOpen(true);
  };

  const closeHistoryModal = () => {
    setHistoryModalOpen(false);
    setCurrentGrantForHistory(null);
    setApplicationHistory([]);
    setHistoryPage(0);
    setHistoryRowsPerPage(5);
  };

  const handleChangeHistoryPage = (event, newPage) => {
    setHistoryPage(newPage);
  };

  const handleChangeHistoryRowsPerPage = (event) => {
    setHistoryRowsPerPage(parseInt(event.target.value, 10));
    setHistoryPage(0);
  };

  if (loading && grants.length === 0) {
    return <Container sx={{ textAlign: 'center', mt: 5 }}><CircularProgress /></Container>;
  }

  // ... existing rendering for stats, charts etc. ...

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" gutterBottom component="h1">
        Grant Dashboard
      </Typography>
      
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={4} md={3}>
            <TextField 
              fullWidth
              label="Search Grants"
              variant="outlined"
              name="searchText" // Add name attribute
              value={filters.searchText || ''} // Use filters.searchText
              onChange={handleFilterChange} // Use handleFilterChange
            />
          </Grid>
          <Grid item xs={12} sm={3} md={2}>
            <FormControl fullWidth>
              <InputLabel>Category</InputLabel>
              <Select
                name="category" // Ensure name attribute is set
                value={filters.category || ''} // Use filters.category
                label="Category"
                onChange={handleFilterChange} // Use handleFilterChange
              >
                <MenuItem value=""><em>All</em></MenuItem>
                <MenuItem value="Research">Research</MenuItem>
                <MenuItem value="Education">Education</MenuItem>
                <MenuItem value="Community">Community</MenuItem>
                {/* Add more categories as needed */}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={2} md={2}>
            <TextField
              fullWidth
              label="Min Score"
              name="minOverallScore"
              type="number"
              value={filters.minOverallScore || ''}
              onChange={handleFilterChange}
              InputProps={{ inputProps: { min: 0, max: 100, step: 1 } }}
            />
          </Grid>
          <Grid item xs={12} sm={2} md={2}>
            <TextField
              fullWidth
              label="Max Score"
              name="maxOverallScore"
              type="number"
              value={filters.maxOverallScore || ''}
              onChange={handleFilterChange}
              InputProps={{ inputProps: { min: 0, max: 100, step: 1 } }}
            />
          </Grid>
          <Grid item xs={12} sm={1} md={1}>
            <Button fullWidth variant="contained" onClick={handleSearch} startIcon={<RefreshIcon />}>
              Search
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {loading && grants.length > 0 && <CircularProgress sx={{ display: 'block', margin: 'auto', mb: 2 }}/>}

      <Grid container spacing={3}>
        {grants.map((grant) => (
          <Grid item key={grant.id} xs={12} sm={6} md={4}>
            <GrantCard 
              grant={grant} 
              onSave={handleSaveGrant} 
              isSaved={savedGrants.has(grant.id)}
            />
            <Box sx={{mt: 1, display: 'flex', justifyContent: 'space-around'}}>
                <Button 
                    size="small" 
                    startIcon={<AddCommentIcon />}
                    onClick={() => openFeedbackModal(grant)}
                >
                    Add Feedback
                </Button>
                <Button 
                    size="small" 
                    startIcon={<VisibilityIcon />}
                    onClick={() => openHistoryModal(grant)}
                >
                    View History
                </Button>
            </Box>
          </Grid>
        ))}
      </Grid>
      {grants.length === 0 && !loading && !error && (
        <Typography sx={{ textAlign: 'center', mt: 5 }}>No grants found matching your criteria.</Typography>
      )}

      {/* Application Feedback Modal */}
      {currentGrantForFeedback && (
        <Dialog open={feedbackModalOpen} onClose={closeFeedbackModal} fullWidth maxWidth="sm">
          <DialogTitle>Submit Application Feedback for: {currentGrantForFeedback.title}</DialogTitle>
          <DialogContent>
            {feedbackError && <Alert severity="error" sx={{ mb: 2 }}>{feedbackError}</Alert>}
            <TextField
              autoFocus
              margin="dense"
              name="submission_date"
              label="Submission Date *"
              type="date"
              fullWidth
              variant="standard"
              value={feedbackData.submission_date || ''}
              onChange={handleFeedbackChange}
              InputLabelProps={{
                shrink: true,
              }}
            />
            <FormControl fullWidth margin="dense" variant="standard">
                <InputLabel id="status-label">Status *</InputLabel>
                <Select
                    labelId="status-label"
                    name="status"
                    value={feedbackData.status || ''}
                    onChange={handleFeedbackChange}
                    label="Status"
                >
                    <MenuItem value="Draft">Draft</MenuItem>
                    <MenuItem value="Submitted">Submitted</MenuItem>
                    <MenuItem value="Under Review">Under Review</MenuItem>
                    <MenuItem value="Awarded">Awarded</MenuItem>
                    <MenuItem value="Rejected">Rejected</MenuItem>
                    <MenuItem value="Withdrawn">Withdrawn</MenuItem>
                    <MenuItem value="Other">Other</MenuItem>
                </Select>
            </FormControl>
            <TextField
              margin="dense"
              name="outcome_notes"
              label="Outcome Notes"
              type="text"
              fullWidth
              multiline
              rows={3}
              variant="standard"
              value={feedbackData.outcome_notes || ''}
              onChange={handleFeedbackChange}
            />
            <TextField
              margin="dense"
              name="feedback_for_profile_update"
              label="Feedback for Profile Update"
              type="text"
              fullWidth
              multiline
              rows={3}
              variant="standard"
              value={feedbackData.feedback_for_profile_update || ''}
              onChange={handleFeedbackChange}
            />
             <TextField
              margin="dense"
              name="status_reason"
              label="Status Reason (e.g., why rejected)"
              type="text"
              fullWidth
              multiline
              rows={2}
              variant="standard"
              value={feedbackData.status_reason || ''}
              onChange={handleFeedbackChange}
            />
            <FormControl fullWidth margin="dense" variant="standard">
                <InputLabel id="is_successful_outcome-label">Was this a successful outcome?</InputLabel>
                <Select
                    labelId="is_successful_outcome-label"
                    name="is_successful_outcome"
                    value={feedbackData.is_successful_outcome === undefined ? '' : String(feedbackData.is_successful_outcome)}
                    onChange={(e) => setFeedbackData(prev => ({...prev, is_successful_outcome: e.target.value === 'true' ? true : e.target.value === 'false' ? false : undefined }))}
                    label="Successful Outcome?"
                >
                    <MenuItem value=""><em>Select...</em></MenuItem>
                    <MenuItem value="true">Yes</MenuItem>
                    <MenuItem value="false">No</MenuItem>
                </Select>
            </FormControl>
          </DialogContent>
          <DialogActions>
            <Button onClick={closeFeedbackModal}>Cancel</Button>
            <Button onClick={handleFeedbackSubmit} disabled={feedbackSubmitting}>
              {feedbackSubmitting ? <CircularProgress size={24} /> : 'Submit'}
            </Button>
          </DialogActions>
        </Dialog>
      )}

      {/* Application History Modal */}
      {currentGrantForHistory && (
        <Dialog open={historyModalOpen} onClose={closeHistoryModal} fullWidth maxWidth="md">
          <DialogTitle>Application History for: {currentGrantForHistory.title}</DialogTitle>
          <DialogContent>
            {historyError && <Alert severity="error" sx={{ mb: 2 }}>{historyError}</Alert>}
            {historyLoading ? (
              <CircularProgress />
            ) : applicationHistory.length > 0 ? (
              <TableContainer component={Paper}>
                <Table sx={{ minWidth: 650 }} aria-label="application history table">
                  <TableHead>
                    <TableRow>
                      <TableCell>Submission Date</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Outcome Notes</TableCell>
                      <TableCell>Profile Feedback</TableCell>
                      <TableCell>Reason</TableCell>
                      <TableCell>Successful?</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {applicationHistory
                      .slice(historyPage * historyRowsPerPage, historyPage * historyRowsPerPage + historyRowsPerPage)
                      .map((entry) => (
                        <TableRow key={entry.id}>
                          <TableCell>{entry.submission_date ? new Date(entry.submission_date).toLocaleDateString() : 'N/A'}</TableCell>
                          <TableCell>{entry.status}</TableCell>
                          <TableCell>{entry.outcome_notes || '-'}</TableCell>
                          <TableCell>{entry.feedback_for_profile_update || '-'}</TableCell>
                          <TableCell>{entry.status_reason || '-'}</TableCell>
                          <TableCell>{entry.is_successful_outcome === undefined ? 'N/A' : entry.is_successful_outcome ? 'Yes' : 'No'}</TableCell>
                        </TableRow>
                    ))}
                  </TableBody>
                </Table>
                <TablePagination
                  rowsPerPageOptions={[5, 10, 25]}
                  component="div"
                  count={applicationHistory.length}
                  rowsPerPage={historyRowsPerPage}
                  page={historyPage}
                  onPageChange={handleChangeHistoryPage}
                  onRowsPerPageChange={handleChangeHistoryRowsPerPage}
                />
              </TableContainer>
            ) : (
              <Typography>No application history found for this grant.</Typography>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={closeHistoryModal}>Close</Button>
          </DialogActions>
        </Dialog>
      )}

    </Container>
  );
};

export default Dashboard;