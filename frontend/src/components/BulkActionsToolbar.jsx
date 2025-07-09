import {
    BookmarkBorder as BookmarkBorderIcon,
    Bookmark as BookmarkIcon,
    Calendar as CalendarIcon,
    Clear as ClearIcon,
    CloudDownload as CloudDownloadIcon,
    TableChart as CsvIcon,
    ExpandMore as ExpandMoreIcon,
    FileCopy as FileCopyIcon,
    PictureAsPdf as PdfIcon
} from '@mui/icons-material';
import {
    Box,
    Button,
    CircularProgress,
    Divider,
    ListItemIcon,
    ListItemText,
    Menu,
    MenuItem,
    Paper,
    Typography
} from '@mui/material';
import { useSnackbar } from 'notistack';
import { useState } from 'react';
import { copyToClipboard, exportToCalendar, exportToCSV, exportToPDF } from '../utils/exportUtils';

const BulkActionsToolbar = ({
  selectedCount,
  selectedGrants,
  onBulkSave,
  onBulkUnsave,
  onClearSelection,
  loading = false,
  showSaveActions = true,
  showExportActions = true
}) => {
  const { enqueueSnackbar } = useSnackbar();
  const [exportMenuAnchor, setExportMenuAnchor] = useState(null);
  const [copyMenuAnchor, setCopyMenuAnchor] = useState(null);

  const handleExportMenuOpen = (event) => {
    setExportMenuAnchor(event.currentTarget);
  };

  const handleExportMenuClose = () => {
    setExportMenuAnchor(null);
  };

  const handleCopyMenuOpen = (event) => {
    setCopyMenuAnchor(event.currentTarget);
  };

  const handleCopyMenuClose = () => {
    setCopyMenuAnchor(null);
  };

  const handleExportCSV = () => {
    try {
      const timestamp = new Date().toISOString().split('T')[0];
      exportToCSV(selectedGrants, `grants_export_${timestamp}.csv`);
      enqueueSnackbar(`${selectedCount} grants exported to CSV`, { variant: 'success' });
      handleExportMenuClose();
    } catch (error) {
      enqueueSnackbar('Failed to export CSV', { variant: 'error' });
    }
  };

  const handleExportPDF = () => {
    try {
      const timestamp = new Date().toISOString().split('T')[0];
      const options = { includeDetails: selectedCount <= 10 };
      exportToPDF(selectedGrants, `grants_report_${timestamp}.pdf`, options);
      enqueueSnackbar(`${selectedCount} grants exported to PDF`, { variant: 'success' });
      handleExportMenuClose();
    } catch (error) {
      enqueueSnackbar('Failed to export PDF', { variant: 'error' });
    }
  };

  const handleExportCalendar = () => {
    try {
      const grantsWithDeadlines = selectedGrants.filter(g => g.deadline || g.deadline_date);
      if (grantsWithDeadlines.length === 0) {
        enqueueSnackbar('No grants with deadlines to export', { variant: 'warning' });
        return;
      }
      
      const timestamp = new Date().toISOString().split('T')[0];
      exportToCalendar(grantsWithDeadlines, `grant_deadlines_${timestamp}.ics`);
      enqueueSnackbar(`${grantsWithDeadlines.length} deadlines exported to calendar`, { variant: 'success' });
      handleExportMenuClose();
    } catch (error) {
      enqueueSnackbar('Failed to export calendar', { variant: 'error' });
    }
  };

  const handleCopyText = async () => {
    try {
      const success = await copyToClipboard(selectedGrants, 'text');
      if (success) {
        enqueueSnackbar(`${selectedCount} grants copied to clipboard`, { variant: 'success' });
      } else {
        enqueueSnackbar('Failed to copy to clipboard', { variant: 'error' });
      }
      handleCopyMenuClose();
    } catch (error) {
      enqueueSnackbar('Failed to copy to clipboard', { variant: 'error' });
    }
  };

  const handleCopyMarkdown = async () => {
    try {
      const success = await copyToClipboard(selectedGrants, 'markdown');
      if (success) {
        enqueueSnackbar(`${selectedCount} grants copied as Markdown`, { variant: 'success' });
      } else {
        enqueueSnackbar('Failed to copy to clipboard', { variant: 'error' });
      }
      handleCopyMenuClose();
    } catch (error) {
      enqueueSnackbar('Failed to copy to clipboard', { variant: 'error' });
    }
  };

  const handleCopyHTML = async () => {
    try {
      const success = await copyToClipboard(selectedGrants, 'html');
      if (success) {
        enqueueSnackbar(`${selectedCount} grants copied as HTML`, { variant: 'success' });
      } else {
        enqueueSnackbar('Failed to copy to clipboard', { variant: 'error' });
      }
      handleCopyMenuClose();
    } catch (error) {
      enqueueSnackbar('Failed to copy to clipboard', { variant: 'error' });
    }
  };

  if (selectedCount === 0) {
    return null;
  }

  return (
    <>
      <Paper 
        sx={{ 
          p: 2, 
          mb: 2, 
          bgcolor: 'primary.50', 
          border: '1px solid', 
          borderColor: 'primary.main',
          borderRadius: 2
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 600, color: 'primary.main' }}>
            {selectedCount} grant{selectedCount !== 1 ? 's' : ''} selected
          </Typography>
          
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            {showSaveActions && (
              <>
                <Button
                  size="small"
                  variant="contained"
                  startIcon={loading ? <CircularProgress size={16} /> : <BookmarkIcon />}
                  onClick={onBulkSave}
                  disabled={loading}
                  sx={{ minWidth: 100 }}
                >
                  Save All
                </Button>
                
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={loading ? <CircularProgress size={16} /> : <BookmarkBorderIcon />}
                  onClick={onBulkUnsave}
                  disabled={loading}
                  sx={{ minWidth: 100 }}
                >
                  Unsave All
                </Button>
              </>
            )}
            
            {showExportActions && (
              <>
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<CloudDownloadIcon />}
                  endIcon={<ExpandMoreIcon />}
                  onClick={handleExportMenuOpen}
                  disabled={loading}
                >
                  Export
                </Button>
                
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<FileCopyIcon />}
                  endIcon={<ExpandMoreIcon />}
                  onClick={handleCopyMenuOpen}
                  disabled={loading}
                >
                  Copy
                </Button>
              </>
            )}
            
            <Button
              size="small"
              startIcon={<ClearIcon />}
              onClick={onClearSelection}
              disabled={loading}
              sx={{ color: 'text.secondary' }}
            >
              Clear
            </Button>
          </Box>
        </Box>
      </Paper>

      {/* Export Menu */}
      <Menu
        anchorEl={exportMenuAnchor}
        open={Boolean(exportMenuAnchor)}
        onClose={handleExportMenuClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
      >
        <MenuItem onClick={handleExportCSV}>
          <ListItemIcon>
            <CsvIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText primary="Export as CSV" secondary="Spreadsheet format" />
        </MenuItem>
        
        <MenuItem onClick={handleExportPDF}>
          <ListItemIcon>
            <PdfIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText 
            primary="Export as PDF" 
            secondary={selectedCount <= 10 ? "With full details" : "Summary only"} 
          />
        </MenuItem>
        
        <Divider />
        
        <MenuItem onClick={handleExportCalendar}>
          <ListItemIcon>
            <CalendarIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText 
            primary="Export Deadlines" 
            secondary="Calendar format (iCal)" 
          />
        </MenuItem>
      </Menu>

      {/* Copy Menu */}
      <Menu
        anchorEl={copyMenuAnchor}
        open={Boolean(copyMenuAnchor)}
        onClose={handleCopyMenuClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
      >
        <MenuItem onClick={handleCopyText}>
          <ListItemText primary="Copy as Text" secondary="Plain text format" />
        </MenuItem>
        
        <MenuItem onClick={handleCopyMarkdown}>
          <ListItemText primary="Copy as Markdown" secondary="Formatted text" />
        </MenuItem>
        
        <MenuItem onClick={handleCopyHTML}>
          <ListItemText primary="Copy as HTML" secondary="Web format" />
        </MenuItem>
      </Menu>
    </>
  );
};

export default BulkActionsToolbar;
