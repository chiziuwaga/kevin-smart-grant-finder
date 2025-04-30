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
    Slider,
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
import React, { useState } from 'react';
import API from '../api/apiClient';

const SearchPage = () => {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('All');
  const [minScore, setMinScore] = useState(70);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const body = { query, category: category === 'All' ? undefined : category, min_score: minScore };
      const data = await API.searchGrants(body);
      setResults(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 3 }}>Search Grants</Typography>
      <Card elevation={2} sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={5}>
              <TextField label="Search query" fullWidth value={query} onChange={(e)=>setQuery(e.target.value)} />
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField select label="Category" fullWidth value={category} onChange={(e)=>setCategory(e.target.value)}>
                {['All','Telecom','Women-Owned Nonprofit','Research','Education','Community','Other'].map(opt=>
                  <MenuItem key={opt} value={opt}>{opt}</MenuItem>
                )}
              </TextField>
            </Grid>
            <Grid item xs={12} md={2}>
              <Typography variant="body2" gutterBottom>Min Relevance: {minScore}%</Typography>
              <Slider value={minScore} onChange={(e, val)=>setMinScore(val)} valueLabelDisplay="auto" min={0} max={100} />
            </Grid>
            <Grid item xs={12} md={2}>
              <Button variant="contained" onClick={handleSearch} fullWidth>Search</Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {loading ? (
        <Box sx={{ display:'flex', justifyContent:'center', mt:4 }}><CircularProgress /></Box>
      ) : results.length ? (
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
              {results.map(res=>(
                <TableRow key={res.id} hover>
                  <TableCell>{res.title}</TableCell>
                  <TableCell>{res.category}</TableCell>
                  <TableCell>{res.deadline ? format(parseISO(res.deadline),'PP') : 'N/A'}</TableCell>
                  <TableCell><Chip label={`${res.relevanceScore || 0}%`} /></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : (
        <Typography variant="body2" color="textSecondary">No results yet. Enter a query and search.</Typography>
      )}
    </Box>
  );
};

export default SearchPage; 