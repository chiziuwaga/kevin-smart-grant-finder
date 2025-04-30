import {
    Box,
    Button,
    Card,
    CardContent,
    Chip,
    CircularProgress,
    Grid,
    MenuItem,
    Paper,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    TextField,
    Typography
} from '@mui/material';
import { format, parseISO } from 'date-fns';
import React, { useEffect, useState } from 'react';
import API from '../api/apiClient';

const GrantsPage = () => {
  const [loading, setLoading] = useState(false);
  const [grants, setGrants] = useState([]);
  const [filters, setFilters] = useState({
    min_score: 0,
    days_to_deadline: 90,
    category: 'All'
  });

  const fetchGrants = async () => {
    setLoading(true);
    try {
      const params = { ...filters };
      if (filters.category === 'All') delete params.category;
      const data = await API.getGrants(params);
      setGrants(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGrants();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFilters((prev) => ({ ...prev, [name]: value }));
  };

  const handleApply = () => fetchGrants();

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 3 }}>All Grants</Typography>

      <Card elevation={2} sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={4} md={3}>
              <TextField
                label="Min Score"
                name="min_score"
                type="number"
                size="small"
                fullWidth
                value={filters.min_score}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12} sm={4} md={3}>
              <TextField
                label="Days to Deadline"
                name="days_to_deadline"
                type="number"
                size="small"
                fullWidth
                value={filters.days_to_deadline}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12} sm={4} md={3}>
              <TextField
                select
                label="Category"
                name="category"
                size="small"
                fullWidth
                value={filters.category}
                onChange={handleChange}
              >
                {['All','Telecom','Women-Owned Nonprofit','Other'].map(opt=>
                  <MenuItem key={opt} value={opt}>{opt}</MenuItem>
                )}
              </TextField>
            </Grid>
            <Grid item xs={12} sm={12} md={3}>
              <Button variant="contained" onClick={handleApply} fullWidth>Apply</Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {loading ? (
        <Box sx={{ display:'flex', justifyContent:'center', mt:4 }}><CircularProgress /></Box>
      ) : (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Title</TableCell>
                <TableCell>Category</TableCell>
                <TableCell>Deadline</TableCell>
                <TableCell>Relevance</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {grants.map(grant => (
                <TableRow key={grant.id} hover>
                  <TableCell>{grant.title}</TableCell>
                  <TableCell>{grant.category}</TableCell>
                  <TableCell>{grant.deadline ? format(parseISO(grant.deadline),'PP'):'N/A'}</TableCell>
                  <TableCell><Chip label={`${grant.relevanceScore || 0}%`} /></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
};

export default GrantsPage; 