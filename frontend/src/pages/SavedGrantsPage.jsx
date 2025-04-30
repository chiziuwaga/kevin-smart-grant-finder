import { Delete as DeleteIcon } from '@mui/icons-material';
import {
    Box,
    Chip,
    CircularProgress,
    IconButton,
    Paper,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Typography
} from '@mui/material';
import { format, parseISO } from 'date-fns';
import React, { useEffect, useState } from 'react';
import API from '../api/apiClient';

const SavedGrantsPage = () => {
  const [loading, setLoading] = useState(true);
  const [grants, setGrants] = useState([]);

  const fetchSaved = async () => {
    setLoading(true);
    try {
      const data = await API.getSavedGrants();
      setGrants(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(()=>{ fetchSaved(); }, []);

  const handleUnsave = async (id) => {
    try {
      await API.unsaveGrant(id);
      setGrants(prev=>prev.filter(g=>g.id!==id));
    } catch(e) {
      console.error(e);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 3 }}>Saved Grants</Typography>
      {loading ? <CircularProgress /> : grants.length ? (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Title</TableCell>
                <TableCell>Category</TableCell>
                <TableCell>Deadline</TableCell>
                <TableCell>Relevance</TableCell>
                <TableCell></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {grants.map(g=>(
                <TableRow key={g.id} hover>
                  <TableCell>{g.title}</TableCell>
                  <TableCell>{g.category}</TableCell>
                  <TableCell>{g.deadline ? format(parseISO(g.deadline),'PP'):'N/A'}</TableCell>
                  <TableCell><Chip label={`${g.relevanceScore || 0}%`} /></TableCell>
                  <TableCell>
                    <IconButton onClick={()=>handleUnsave(g.id)}><DeleteIcon /></IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : <Typography>No saved grants.</Typography>}
    </Box>
  );
};

export default SavedGrantsPage; 