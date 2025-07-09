import {
  AddComment as AddCommentIcon,
  CheckBox as CheckboxIcon,
  CloudDownload as CloudDownloadIcon,
  Refresh as RefreshIcon,
  Visibility as VisibilityIcon,
} from '@mui/icons-material';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  CircularProgress,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  Grid,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Snackbar,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import { useCallback, useEffect, useState } from 'react';
import apiClient from '../api/apiClient'; // apiClient will be the compiled JS version of apiClient.ts
import GrantCard from './GrantCard';
import GrantDetailsModal from './GrantDetailsModal';
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

  // Bulk operations state
  const [selectedGrants, setSelectedGrants] = useState(new Set());
  const [bulkActionMode, setBulkActionMode] = useState(false);
  const [bulkLoading, setBulkLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  const [filters, setFilters] = useState({
    searchText: '',
    category: '',
    minOverallScore: '', // New filter for minimum overall_composite_score
    maxOverallScore: '', // New filter for maximum overall_composite_score
    includeExpired: false, // Filter to include/exclude expired grants
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

  // Grant Details Modal
  const [detailsModalOpen, setDetailsModalOpen] = useState(false);
  const [currentGrantForDetails, setCurrentGrantForDetails] = useState(null);

  const handleViewDetails = (grant) => {
    setCurrentGrantForDetails(grant);
    setDetailsModalOpen(true);
  };

  const handleCloseDetails = () => {
    setDetailsModalOpen(false);
    setCurrentGrantForDetails(null);
  };

  const fetchGrants = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Use searchText and category from filters state
      const {
        searchText,
        category,
        minOverallScore,
        maxOverallScore,
        includeExpired,
        ...otherFilters
      } = filters;
      const params = {
        searchText: searchText || undefined,
        category: category || undefined,
        min_overall_score: minOverallScore
          ? parseFloat(minOverallScore)
          : undefined, // Pass to backend
        max_overall_score: maxOverallScore
          ? parseFloat(maxOverallScore)
          : undefined, // Pass to backend
        ...otherFilters,
      };
      const response = await apiClient.getGrants(params);
      let grantsData = response.items;

      // Client-side filtering for expired grants if not including expired
      if (!includeExpired) {
        grantsData = grantsData.filter((grant) => {
          const deadline = grant.deadline || grant.deadline_date;
          if (!deadline) return true; // Include grants without deadlines

          const deadlineDate = new Date(deadline);
          const today = new Date();
          return deadlineDate >= today; // Only include non-expired grants
        });
      }

      setGrants(grantsData);
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
        setSavedGrants(new Set(response.items.map((g) => g.id)));
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
        setSavedGrants((prev) => new Set(prev).add(grantId));
      } else {
        await apiClient.unsaveGrant(grantId);
        setSavedGrants((prev) => {
          const next = new Set(prev);
          next.delete(grantId);
          return next;
        });
      }
    } catch (err) {
      console.error(`Failed to ${save ? 'save' : 'unsave'} grant:`, err);
      setError(
        `Failed to ${save ? 'save' : 'unsave'} grant. Please try again.`
      );
    }
  };

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters((prev) => ({ ...prev, [name]: value }));
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
    setFeedbackData((prev) => ({ ...prev, [name]: value }));
  };

  const handleFeedbackSubmit = async () => {
    if (
      !currentGrantForFeedback ||
      !feedbackData.grant_id ||
      !feedbackData.status ||
      !feedbackData.submission_date
    ) {
      setFeedbackError(
        'Please fill in all required fields (status, submission date).'
      );
      return;
    }
    setFeedbackSubmitting(true);
    setFeedbackError(null);
    try {
      await apiClient.submitApplicationFeedback(feedbackData);
      closeFeedbackModal();
      alert('Feedback submitted successfully!');
      // Optionally, refresh history if the current grant's history was open
      if (
        currentGrantForHistory &&
        currentGrantForHistory.id === feedbackData.grant_id
      ) {
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

  // Bulk operations handlers
  const handleSelectGrant = (grantId, selected) => {
    setSelectedGrants((prev) => {
      const newSet = new Set(prev);
      if (selected) {
        newSet.add(grantId);
      } else {
        newSet.delete(grantId);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    if (selectedGrants.size === grants.length) {
      setSelectedGrants(new Set());
    } else {
      setSelectedGrants(new Set(grants.map((g) => g.id)));
    }
  };

  const handleBulkSave = async () => {
    setBulkLoading(true);
    try {
      const savePromises = Array.from(selectedGrants).map((grantId) =>
        apiClient.saveGrant(grantId)
      );
      await Promise.all(savePromises);

      // Update saved grants state
      setSavedGrants((prev) => {
        const newSet = new Set(prev);
        selectedGrants.forEach((id) => newSet.add(id));
        return newSet;
      });

      setSelectedGrants(new Set());
      setBulkActionMode(false);
      setSuccessMessage(`Successfully saved ${selectedGrants.size} grants`);
    } catch (err) {
      setError('Failed to save selected grants');
    }
    setBulkLoading(false);
  };

  const handleBulkUnsave = async () => {
    setBulkLoading(true);
    try {
      const unsavePromises = Array.from(selectedGrants).map((grantId) =>
        apiClient.unsaveGrant(grantId)
      );
      await Promise.all(unsavePromises);

      // Update saved grants state
      setSavedGrants((prev) => {
        const newSet = new Set(prev);
        selectedGrants.forEach((id) => newSet.delete(id));
        return newSet;
      });

      setSelectedGrants(new Set());
      setBulkActionMode(false);
      setSuccessMessage(`Successfully unsaved ${selectedGrants.size} grants`);
    } catch (err) {
      setError('Failed to unsave selected grants');
    }
    setBulkLoading(false);
  };

  const handleBulkExportCSV = () => {
    const selectedGrantsData = grants.filter((grant) =>
      selectedGrants.has(grant.id)
    );
    const csvContent = generateCSV(selectedGrantsData);
    downloadCSV(
      csvContent,
      `grants_export_${new Date().toISOString().split('T')[0]}.csv`
    );
    setSelectedGrants(new Set());
    setBulkActionMode(false);
    setSuccessMessage(
      `Successfully exported ${selectedGrantsData.length} grants to CSV`
    );
  };

  const handleBulkExportICS = () => {
    const selectedGrantsData = grants.filter((grant) =>
      selectedGrants.has(grant.id)
    );
    const icsContent = generateICS(selectedGrantsData);
    downloadICS(
      icsContent,
      `grant_deadlines_${new Date().toISOString().split('T')[0]}.ics`
    );
    setSelectedGrants(new Set());
    setBulkActionMode(false);
    setSuccessMessage(
      `Successfully exported ${selectedGrantsData.length} grant deadlines to calendar`
    );
  };

  const generateICS = (grantsData) => {
    const icsHeader = [
      'BEGIN:VCALENDAR',
      'VERSION:2.0',
      'PRODID:-//Smart Grant Finder//Grant Calendar//EN',
      'CALSCALE:GREGORIAN',
      'METHOD:PUBLISH',
    ].join('\r\n');

    const icsFooter = 'END:VCALENDAR';

    const events = grantsData
      .filter((grant) => grant.deadline || grant.deadline_date)
      .map((grant) => {
        const deadline = grant.deadline || grant.deadline_date;
        const deadlineDate = new Date(deadline);
        const formattedDate =
          deadlineDate.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';

        return [
          'BEGIN:VEVENT',
          `UID:grant-${grant.id}@smartgrantfinder.com`,
          `DTSTAMP:${
            new Date().toISOString().replace(/[-:]/g, '').split('.')[0]
          }Z`,
          `DTSTART:${formattedDate}`,
          `SUMMARY:Grant Deadline: ${grant.title}`,
          `DESCRIPTION:Grant application deadline for ${
            grant.title
          }\\nFunder: ${grant.funder_name || 'Unknown'}\\nAmount: ${
            grant.funding_amount_display || 'Not specified'
          }\\nScore: ${grant.overall_composite_score || 'N/A'}`,
          `LOCATION:${grant.geographic_scope || 'Various'}`,
          `URL:${grant.source_url || ''}`,
          'STATUS:CONFIRMED',
          'TRANSP:TRANSPARENT',
          'END:VEVENT',
        ].join('\r\n');
      });

    return [icsHeader, ...events, icsFooter].join('\r\n');
  };

  const handleBulkExportPDF = () => {
    const selectedGrantsData = grants.filter((grant) =>
      selectedGrants.has(grant.id)
    );
    generatePDF(selectedGrantsData);
    setSelectedGrants(new Set());
    setBulkActionMode(false);
    setSuccessMessage(
      `Successfully exported ${selectedGrantsData.length} grants to PDF`
    );
  };

  const generatePDF = (grantsData) => {
    // Create a new window with the grant data formatted for printing
    const printWindow = window.open('', '_blank');
    const htmlContent = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>Grant Details Export</title>
          <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .grant { border: 1px solid #ddd; margin: 20px 0; padding: 15px; page-break-inside: avoid; }
            .grant-title { font-size: 18px; font-weight: bold; color: #1976d2; margin-bottom: 10px; }
            .grant-info { margin: 5px 0; }
            .grant-description { margin: 10px 0; line-height: 1.5; }
            .scores { background: #f5f5f5; padding: 10px; margin: 10px 0; }
            .score-item { display: inline-block; margin: 5px 10px 5px 0; }
            @media print {
              body { margin: 0; }
              .grant { margin: 10px 0; page-break-inside: avoid; }
            }
          </style>
        </head>
        <body>
          <h1>Grant Details Export</h1>
          <p>Exported on: ${new Date().toLocaleDateString()}</p>
          <p>Total Grants: ${grantsData.length}</p>
          ${grantsData
            .map(
              (grant) => `
            <div class="grant">
              <div class="grant-title">${grant.title || 'Untitled Grant'}</div>
              <div class="grant-info"><strong>Funder:</strong> ${
                grant.funder_name || 'Unknown'
              }</div>
              <div class="grant-info"><strong>Category:</strong> ${
                grant.category || grant.identified_sector || 'Other'
              }</div>
              <div class="grant-info"><strong>Deadline:</strong> ${
                grant.deadline || grant.deadline_date || 'Not specified'
              }</div>
              <div class="grant-info"><strong>Funding Amount:</strong> ${
                grant.funding_amount_display ||
                grant.fundingAmount ||
                'Not specified'
              }</div>
              <div class="grant-info"><strong>Geographic Scope:</strong> ${
                grant.geographic_scope || 'Not specified'
              }</div>
              <div class="grant-info"><strong>Relevance Score:</strong> ${
                grant.overall_composite_score
                  ? grant.overall_composite_score.toFixed(1)
                  : grant.relevanceScore || 'N/A'
              }</div>
              <div class="grant-description">
                <strong>Description:</strong><br>
                ${grant.description || 'No description available'}
              </div>
              ${
                grant.summary_llm
                  ? `
                <div class="grant-description">
                  <strong>AI Summary:</strong><br>
                  ${grant.summary_llm}
                </div>
              `
                  : ''
              }
              ${
                grant.eligibility_summary_llm
                  ? `
                <div class="grant-description">
                  <strong>Eligibility Requirements:</strong><br>
                  ${grant.eligibility_summary_llm}
                </div>
              `
                  : ''
              }
              ${
                grant.keywords && grant.keywords.length > 0
                  ? `
                <div class="grant-info"><strong>Keywords:</strong> ${grant.keywords.join(
                  ', '
                )}</div>
              `
                  : ''
              }
              ${
                grant.source_url || grant.sourceUrl
                  ? `
                <div class="grant-info"><strong>Source:</strong> <a href="${
                  grant.source_url || grant.sourceUrl
                }" target="_blank">${
                      grant.source_url || grant.sourceUrl
                    }</a></div>
              `
                  : ''
              }
            </div>
          `
            )
            .join('')}
        </body>
      </html>
    `;

    printWindow.document.write(htmlContent);
    printWindow.document.close();

    // Auto-print the window
    printWindow.onload = () => {
      printWindow.print();
    };
  };

  const downloadICS = (content, filename) => {
    const blob = new Blob([content], { type: 'text/calendar;charset=utf-8;' });
    const link = document.createElement('a');
    if (link.download !== undefined) {
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', filename);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  const generateCSV = (grantsData) => {
    const headers = [
      'Title',
      'Category',
      'Funder',
      'Deadline',
      'Funding Amount',
      'Relevance Score',
      'Description',
      'Source URL',
    ];

    const rows = grantsData.map((grant) => [
      grant.title || '',
      grant.category || grant.identified_sector || '',
      grant.funder_name || '',
      grant.deadline || grant.deadline_date || '',
      grant.funding_amount_display || grant.fundingAmount || '',
      grant.overall_composite_score || grant.relevanceScore || '',
      grant.description || '',
      grant.source_url || grant.sourceUrl || '',
    ]);

    return [headers, ...rows]
      .map((row) =>
        row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(',')
      )
      .join('\n');
  };

  const downloadCSV = (content, filename) => {
    const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    if (link.download !== undefined) {
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', filename);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  if (loading && grants.length === 0) {
    return (
      <Container sx={{ textAlign: 'center', mt: 5 }}>
        <CircularProgress />
      </Container>
    );
  }

  // ... existing rendering for stats, charts etc. ...

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          mb: 3,
        }}
      >
        <Typography variant="h4" component="h1">
          Grant Dashboard
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant={bulkActionMode ? 'contained' : 'outlined'}
            onClick={() => setBulkActionMode(!bulkActionMode)}
            startIcon={<CheckboxIcon />}
          >
            {bulkActionMode ? 'Exit Bulk Mode' : 'Bulk Actions'}
          </Button>
        </Box>
      </Box>

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
                <MenuItem value="">
                  <em>All</em>
                </MenuItem>
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
          <Grid item xs={12} sm={2} md={2}>
            <FormControlLabel
              control={
                <Checkbox
                  name="includeExpired"
                  checked={filters.includeExpired}
                  onChange={(e) =>
                    setFilters((prev) => ({
                      ...prev,
                      includeExpired: e.target.checked,
                    }))
                  }
                />
              }
              label="Include Expired"
            />
          </Grid>
          <Grid item xs={12} sm={1} md={1}>
            <Button
              fullWidth
              variant="contained"
              onClick={handleSearch}
              startIcon={<RefreshIcon />}
            >
              Search
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      {loading && grants.length > 0 && (
        <CircularProgress sx={{ display: 'block', margin: 'auto', mb: 2 }} />
      )}

      {bulkActionMode ? (
        <Paper sx={{ p: 2, mb: 3 }}>
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              mb: 2,
            }}
          >
            <Typography variant="h6">
              Bulk Actions ({selectedGrants.size} selected)
            </Typography>
            <Button variant="outlined" size="small" onClick={handleSelectAll}>
              {selectedGrants.size === grants.length
                ? 'Deselect All'
                : 'Select All'}
            </Button>
          </Box>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <Button
                fullWidth
                variant="contained"
                onClick={handleBulkSave}
                disabled={selectedGrants.size === 0 || bulkLoading}
                startIcon={
                  bulkLoading ? (
                    <CircularProgress size={16} />
                  ) : (
                    <AddCommentIcon />
                  )
                }
              >
                Save Grants
              </Button>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Button
                fullWidth
                variant="outlined"
                onClick={handleBulkUnsave}
                disabled={selectedGrants.size === 0 || bulkLoading}
                startIcon={
                  bulkLoading ? (
                    <CircularProgress size={16} />
                  ) : (
                    <VisibilityIcon />
                  )
                }
              >
                Unsave Grants
              </Button>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Button
                fullWidth
                variant="outlined"
                onClick={handleBulkExportCSV}
                disabled={selectedGrants.size === 0 || bulkLoading}
                startIcon={
                  bulkLoading ? (
                    <CircularProgress size={16} />
                  ) : (
                    <CloudDownloadIcon />
                  )
                }
              >
                Export CSV
              </Button>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Button
                fullWidth
                variant="outlined"
                onClick={handleBulkExportICS}
                disabled={selectedGrants.size === 0 || bulkLoading}
                startIcon={
                  bulkLoading ? (
                    <CircularProgress size={16} />
                  ) : (
                    <CloudDownloadIcon />
                  )
                }
              >
                Export Calendar
              </Button>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Button
                fullWidth
                variant="outlined"
                onClick={handleBulkExportPDF}
                disabled={selectedGrants.size === 0 || bulkLoading}
                startIcon={
                  bulkLoading ? (
                    <CircularProgress size={16} />
                  ) : (
                    <CloudDownloadIcon />
                  )
                }
              >
                Export PDF
              </Button>
            </Grid>
          </Grid>
          <Button
            variant="text"
            onClick={() => setBulkActionMode(false)}
            sx={{ mt: 2 }}
          >
            Cancel
          </Button>
        </Paper>
      ) : null}

      <Grid container spacing={3}>
        {grants.map((grant) => (
          <Grid item key={grant.id} xs={12} sm={6} md={4}>
            <GrantCard
              grant={grant}
              onSave={handleSaveGrant}
              isSaved={savedGrants.has(grant.id)}
              onViewDetails={handleViewDetails}
              onSelect={handleSelectGrant}
              isSelected={selectedGrants.has(grant.id)}
              bulkActionMode={bulkActionMode}
            />
            <Box
              sx={{ mt: 1, display: 'flex', justifyContent: 'space-around' }}
            >
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
        <Typography sx={{ textAlign: 'center', mt: 5 }}>
          No grants found matching your criteria.
        </Typography>
      )}

      {/* Application Feedback Modal */}
      {currentGrantForFeedback && (
        <Dialog
          open={feedbackModalOpen}
          onClose={closeFeedbackModal}
          fullWidth
          maxWidth="sm"
        >
          <DialogTitle>
            Submit Application Feedback for: {currentGrantForFeedback.title}
          </DialogTitle>
          <DialogContent>
            {feedbackError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {feedbackError}
              </Alert>
            )}
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
              <InputLabel id="is_successful_outcome-label">
                Was this a successful outcome?
              </InputLabel>
              <Select
                labelId="is_successful_outcome-label"
                name="is_successful_outcome"
                value={
                  feedbackData.is_successful_outcome === undefined
                    ? ''
                    : String(feedbackData.is_successful_outcome)
                }
                onChange={(e) =>
                  setFeedbackData((prev) => ({
                    ...prev,
                    is_successful_outcome:
                      e.target.value === 'true'
                        ? true
                        : e.target.value === 'false'
                        ? false
                        : undefined,
                  }))
                }
                label="Successful Outcome?"
              >
                <MenuItem value="">
                  <em>Select...</em>
                </MenuItem>
                <MenuItem value="true">Yes</MenuItem>
                <MenuItem value="false">No</MenuItem>
              </Select>
            </FormControl>
          </DialogContent>
          <DialogActions>
            <Button onClick={closeFeedbackModal}>Cancel</Button>
            <Button
              onClick={handleFeedbackSubmit}
              disabled={feedbackSubmitting}
            >
              {feedbackSubmitting ? <CircularProgress size={24} /> : 'Submit'}
            </Button>
          </DialogActions>
        </Dialog>
      )}

      {/* Application History Modal */}
      {currentGrantForHistory && (
        <Dialog
          open={historyModalOpen}
          onClose={closeHistoryModal}
          fullWidth
          maxWidth="md"
        >
          <DialogTitle>
            Application History for: {currentGrantForHistory.title}
          </DialogTitle>
          <DialogContent>
            {historyError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {historyError}
              </Alert>
            )}
            {historyLoading ? (
              <CircularProgress />
            ) : applicationHistory.length > 0 ? (
              <TableContainer component={Paper}>
                <Table
                  sx={{ minWidth: 650 }}
                  aria-label="application history table"
                >
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
                      .slice(
                        historyPage * historyRowsPerPage,
                        historyPage * historyRowsPerPage + historyRowsPerPage
                      )
                      .map((entry) => (
                        <TableRow key={entry.id}>
                          <TableCell>
                            {entry.submission_date
                              ? new Date(
                                  entry.submission_date
                                ).toLocaleDateString()
                              : 'N/A'}
                          </TableCell>
                          <TableCell>{entry.status}</TableCell>
                          <TableCell>{entry.outcome_notes || '-'}</TableCell>
                          <TableCell>
                            {entry.feedback_for_profile_update || '-'}
                          </TableCell>
                          <TableCell>{entry.status_reason || '-'}</TableCell>
                          <TableCell>
                            {entry.is_successful_outcome === undefined
                              ? 'N/A'
                              : entry.is_successful_outcome
                              ? 'Yes'
                              : 'No'}
                          </TableCell>
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
              <Typography>
                No application history found for this grant.
              </Typography>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={closeHistoryModal}>Close</Button>
          </DialogActions>
        </Dialog>
      )}

      {/* Grant Details Modal */}
      <GrantDetailsModal
        grant={currentGrantForDetails}
        open={detailsModalOpen}
        onClose={handleCloseDetails}
      />

      {/* Success Snackbar */}
      <Snackbar
        open={Boolean(successMessage)}
        autoHideDuration={4000}
        onClose={() => setSuccessMessage('')}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setSuccessMessage('')}
          severity="success"
          sx={{ width: '100%' }}
        >
          {successMessage}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default Dashboard;
