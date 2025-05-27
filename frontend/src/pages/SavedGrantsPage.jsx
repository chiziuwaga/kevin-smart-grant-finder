import {
    Bookmark as BookmarkIcon,
    Delete as DeleteIcon
} from '@mui/icons-material';
import {
    Box,
    Chip,
    IconButton,
    Paper,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Typography,
    useTheme,
    alpha,
} from '@mui/material';
import { format, parseISO, differenceInDays } from 'date-fns';
import { useSnackbar } from 'notistack';
import React, { useEffect, useState } from 'react';
import API from '../api/apiClient';
import LoaderOverlay from '../components/common/LoaderOverlay';
import EmptyState from '../components/common/EmptyState';
import TableSkeleton from '../components/common/TableSkeleton';

const SavedGrantsPage = () => {
  const theme = useTheme();
  const { enqueueSnackbar } = useSnackbar();
  const [loading, setLoading] = useState(true);
  const [grants, setGrants] = useState([]);

  const fetchSaved = async () => {
    setLoading(true);
    try {
      const data = await API.getSavedGrants();
      setGrants(data);
    } catch (e) {
      console.error(e);
      enqueueSnackbar('Failed to load saved grants', { variant: 'error' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { 
    fetchSaved(); 
  }, []);

  const handleUnsave = async (id) => {
    try {
      await API.unsaveGrant(id);
      setGrants(prev => prev.filter(g => g.id !== id));
      enqueueSnackbar('Grant removed from saved items', { variant: 'success' });
    } catch(e) {
      console.error(e);
      enqueueSnackbar('Failed to remove grant', { variant: 'error' });
    }
  };

  const getRelevanceColor = (score) => {
    if (score >= 90) return theme.palette.success.main;
    if (score >= 80) return theme.palette.info.main;
    if (score >= 70) return theme.palette.warning.main;
    return theme.palette.error.main;
  };

  return (
    <Box sx={{ p: { xs: 2, sm: 3 } }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <BookmarkIcon sx={{ mr: 2, color: 'primary.main' }} />
        <Typography 
          variant="h4" 
          sx={{ 
            fontWeight: 700,
            fontSize: { xs: '1.5rem', sm: '2rem' }
          }}
        >
          Saved Grants
        </Typography>
      </Box>

      <LoaderOverlay loading={loading}>
        {grants.length > 0 ? (
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
                  <TableCell align="center">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {loading ? (
                  <TableSkeleton rows={5} columns={5} />
                ) : (
                  grants.map(grant => {
                    const daysToDeadline = grant.deadline ? 
                      differenceInDays(parseISO(grant.deadline), new Date()) : null;
                    
                    return (
                      <TableRow 
                        key={grant.id} 
                        hover
                        sx={{
                          '&:hover': {
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
                        <TableCell align="center">
                          <IconButton 
                            onClick={() => handleUnsave(grant.id)}
                            color="error"
                            size="small"
                            title="Remove from saved"
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
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
            message="No saved grants yet"
            icon={BookmarkIcon}
          />
        )}
      </LoaderOverlay>
    </Box>
  );
};

export default SavedGrantsPage;