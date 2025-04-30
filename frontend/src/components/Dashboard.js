import {
  AccessTime as AccessTimeIcon,
  Assessment as AssessmentIcon,
  AttachMoney as AttachMoneyIcon,
  BookmarkBorder as BookmarkBorderIcon,
  Bookmark as BookmarkIcon,
  InfoOutlined as InfoOutlinedIcon,
  NotificationsActive as NotificationsActiveIcon,
  TrendingUp as TrendingUpIcon
} from '@mui/icons-material';
import {
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  IconButton,
  Link as MuiLink,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  useTheme
} from '@mui/material';
import { differenceInDays, format, parseISO } from 'date-fns';
import React, { useEffect, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts';
import API from '../api/apiClient';

const Dashboard = () => {
  const theme = useTheme();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [highPriorityGrants, setHighPriorityGrants] = useState([]);
  const [deadlineSoonGrants, setDeadlineSoonGrants] = useState([]);
  const [chartData, setChartData] = useState({
    deadlines: [],
    categories: [],
    relevanceDistribution: []
  });
  const [savedGrants, setSavedGrants] = useState(new Set());

  useEffect(() => {
    const fetchDashboardData = async () => {
      setLoading(true);
      try {
        const statsResponse = await API.getDashboardStats();
        const highPriorityResponse = await API.getGrants({ min_score: 85, limit: 5 });
        const deadlineSoonResponse = await API.getGrants({ days_to_deadline: 7, limit: 5 });
        const savedGrantsResponse = await API.getSavedGrants();

        setStats(statsResponse.data);
        setHighPriorityGrants(highPriorityResponse.data);
        setDeadlineSoonGrants(deadlineSoonResponse.data);
        setSavedGrants(new Set(savedGrantsResponse.data.map(g => g.id)));

        const mockDeadlineChart = [
          { name: 'This Week', count: deadlineSoonResponse.data.length },
          { name: '1-2 Weeks', count: 7 },
          { name: '3-4 Weeks', count: 12 },
          { name: '1-2 Months', count: 25 },
          { name: '3+ Months', count: 42 }
        ];

        const mockCategoriesChart = [
          { name: 'Research', value: 58 },
          { name: 'Education', value: 42 },
          { name: 'Community', value: 35 },
          { name: 'Other', value: 56 }
        ];
        
        const mockRelevanceChart = [
          { name: '90-100', value: 12 },
          { name: '80-89', value: 30 },
          { name: '70-79', value: 45 },
          { name: '< 70', value: 90 }
        ];

        setChartData({
          deadlines: mockDeadlineChart,
          categories: mockCategoriesChart,
          relevanceDistribution: mockRelevanceChart
        });

      } catch (error) {
        console.error('Error fetching dashboard data:', error);
        setStats({ totalGrants: 'N/A', highPriorityCount: 'N/A', deadlineSoonCount: 'N/A', savedGrantsCount: 'N/A', totalFunding: 'N/A', averageRelevanceScore: 'N/A' });
        setHighPriorityGrants([]);
        setDeadlineSoonGrants([]);
        setChartData({ deadlines: [], categories: [], relevanceDistribution: [] });
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  const handleSaveGrant = async (grantId, shouldSave) => {
    try {
      if (shouldSave) {
        await API.saveGrant(grantId);
        setSavedGrants(prev => new Set(prev).add(grantId));
      } else {
        await API.unsaveGrant(grantId);
        setSavedGrants(prev => {
          const next = new Set(prev);
          next.delete(grantId);
          return next;
        });
      }
    } catch (error) {
      console.error("Error saving/unsaving grant:", error);
    }
  };

  const categoryColors = {
    Research: theme.palette.info.main,
    Education: theme.palette.success.main,
    Community: theme.palette.warning.main,
    Healthcare: theme.palette.error.main,
    Environment: theme.palette.secondary.main,
    Arts: '#9c27b0',
    Business: '#795548',
    Energy: '#607d8b',
    Other: theme.palette.grey[500]
  };

  const COLORS = [
    theme.palette.primary.main,
    theme.palette.secondary.main,
    theme.palette.info.main,
    theme.palette.success.main,
    theme.palette.warning.main,
    theme.palette.error.main,
  ];

  if (loading || !stats) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  const renderGrantRow = (grant) => {
    const daysToDeadline = differenceInDays(
      parseISO(grant.deadline),
      new Date()
    );
    const isSaved = savedGrants.has(grant.id);

    return (
      <TableRow 
        key={grant.id}
        hover
        sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
      >
        <TableCell component="th" scope="row">
            <MuiLink 
              component="button"
              variant="subtitle1" 
              onClick={() => {/* TODO: Open grant detail modal or navigate */}}
              sx={{ fontWeight: 'bold', textAlign: 'left', color: 'primary.main' }}
            >
              {grant.title}
            </MuiLink>
            <Typography variant="body2" color="textSecondary" sx={{ display: 'block' }}>
              {grant.source}
            </Typography>
        </TableCell>
        <TableCell>
          <Chip 
            label={grant.category} 
            size="small" 
            sx={{ 
              backgroundColor: categoryColors[grant.category] || categoryColors.Other,
              color: 'white'
            }}
          />
        </TableCell>
        <TableCell>
          <Box sx={{ display: 'flex', alignItems: 'center', whiteSpace: 'nowrap' }}>
            <AccessTimeIcon fontSize="small" sx={{ mr: 0.5, color: daysToDeadline < 14 ? theme.palette.error.main : theme.palette.text.secondary }} />
            <Typography variant="body2">
              {format(parseISO(grant.deadline), 'PP')}
              <Typography component="span" variant="caption" sx={{ color: 'text.secondary', ml: 0.5 }}>
                ({daysToDeadline}d)
              </Typography>
            </Typography>
          </Box>
        </TableCell>
        <TableCell>
          <Typography variant="body2">{grant.fundingAmount || 'N/A'}</Typography>
        </TableCell>
        <TableCell>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <Chip 
              label={grant.relevanceScore}
              size="small"
              color={grant.relevanceScore >= 90 ? "success" : grant.relevanceScore >= 80 ? "info" : "warning"}
              variant="outlined"
            />
          </Box>
        </TableCell>
        <TableCell align="right">
            <IconButton 
              size="small"
              onClick={() => handleSaveGrant(grant.id, !isSaved)} 
              color={isSaved ? "secondary" : "default"}
              title={isSaved ? "Unsave Grant" : "Save Grant"}
            >
              {isSaved ? <BookmarkIcon /> : <BookmarkBorderIcon />}
            </IconButton>
            <IconButton 
              size="small" 
              href={grant.sourceUrl} 
              target="_blank" 
              rel="noopener noreferrer"
              title="View Original Source"
              sx={{ ml: 1 }}
            >
              <InfoOutlinedIcon fontSize="small" />
            </IconButton>
        </TableCell>
      </TableRow>
    );
  };

  return (
    <Box sx={{ p: 3, backgroundColor: theme.palette.background.default, minHeight: 'calc(100vh - 64px)' }}>
      <Typography variant="h4" sx={{ mb: 3, fontWeight: 700 }}>
        Dashboard
      </Typography>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={4} lg={2}>
          <Card elevation={2}>
            <CardContent sx={{ textAlign: 'center' }}>
              <TrendingUpIcon color="primary" sx={{ fontSize: 36, mb: 1 }} />
              <Typography variant="h5" sx={{ fontWeight: 600 }}>{stats.totalGrants}</Typography>
              <Typography variant="body2" color="textSecondary">Total Grants Found</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={4} lg={2}>
          <Card elevation={2} sx={{ bgcolor: theme.palette.info.lighter, borderLeft: `4px solid ${theme.palette.info.main}` }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <AssessmentIcon sx={{ fontSize: 36, mb: 1, color: theme.palette.info.dark }} />
              <Typography variant="h5" sx={{ fontWeight: 600, color: theme.palette.info.darker }}>{stats.highPriorityCount}</Typography>
              <Typography variant="body2" sx={{ color: theme.palette.info.dark }}>High Priority</Typography>
            </CardContent>
          </Card>
        </Grid>
         <Grid item xs={12} sm={6} md={4} lg={2}>
          <Card elevation={2} sx={{ bgcolor: theme.palette.warning.lighter, borderLeft: `4px solid ${theme.palette.warning.main}` }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <AccessTimeIcon sx={{ fontSize: 36, mb: 1, color: theme.palette.warning.dark }} />
              <Typography variant="h5" sx={{ fontWeight: 600, color: theme.palette.warning.darker }}>{stats.deadlineSoonCount}</Typography>
              <Typography variant="body2" sx={{ color: theme.palette.warning.dark }}>Due Soon (7d)</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={4} lg={2}>
          <Card elevation={2}>
            <CardContent sx={{ textAlign: 'center' }}>
              <BookmarkIcon color="secondary" sx={{ fontSize: 36, mb: 1 }} />
              <Typography variant="h5" sx={{ fontWeight: 600 }}>{stats.savedGrantsCount}</Typography>
              <Typography variant="body2" color="textSecondary">Saved Grants</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={4} lg={2}>
          <Card elevation={2}>
            <CardContent sx={{ textAlign: 'center' }}>
              <AttachMoneyIcon color="success" sx={{ fontSize: 36, mb: 1 }} />
              <Typography variant="h5" sx={{ fontWeight: 600 }}>{stats.totalFunding || 'N/A'}</Typography>
              <Typography variant="body2" color="textSecondary">Total Funding</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={4} lg={2}>
          <Card elevation={2}>
            <CardContent sx={{ textAlign: 'center' }}>
              <NotificationsActiveIcon color="action" sx={{ fontSize: 36, mb: 1 }} />
              <Typography variant="h5" sx={{ fontWeight: 600 }}>{stats.averageRelevanceScore || 'N/A'}%</Typography>
              <Typography variant="body2" color="textSecondary">Avg. Relevance</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3} sx={{ mb: 4 }}>
         <Grid item xs={12} md={4}>
          <Card elevation={2} sx={{ height: 320 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>Deadlines Distribution</Typography>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={chartData.deadlines} margin={{ top: 5, right: 5, left: -25, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false}/>
                  <XAxis dataKey="name" fontSize={12} />
                  <YAxis fontSize={12} />
                  <Tooltip />
                  <Bar dataKey="count" fill={theme.palette.primary.main} radius={[4, 4, 0, 0]}/>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card elevation={2} sx={{ height: 320 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>Grant Categories</Typography>
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie
                    data={chartData.categories}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    fontSize={12}
                  >
                    {chartData.categories.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card elevation={2} sx={{ height: 320 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>Relevance Distribution</Typography>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={chartData.relevanceDistribution} layout="vertical" margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false}/>
                  <XAxis type="number" fontSize={12} />
                  <YAxis dataKey="name" type="category" width={50} fontSize={12} />
                  <Tooltip />
                  <Bar dataKey="value" fill={theme.palette.secondary.main} radius={[0, 4, 4, 0]}/>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        <Grid item xs={12} lg={6}>
          <Typography variant="h5" sx={{ mb: 2 }}>High Priority Grants</Typography>
          <TableContainer component={Paper} elevation={2}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Grant</TableCell>
                  <TableCell>Category</TableCell>
                  <TableCell>Deadline</TableCell>
                  <TableCell>Amount</TableCell>
                  <TableCell>Score</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {highPriorityGrants.length > 0 ? 
                  highPriorityGrants.map(grant => renderGrantRow(grant)) : 
                  <TableRow><TableCell colSpan={6} align="center">No high priority grants found matching current criteria.</TableCell></TableRow>}
              </TableBody>
            </Table>
          </TableContainer>
        </Grid>

        <Grid item xs={12} lg={6}>
          <Typography variant="h5" sx={{ mb: 2 }}>Deadlines Soon</Typography>
          <TableContainer component={Paper} elevation={2}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Grant</TableCell>
                  <TableCell>Category</TableCell>
                  <TableCell>Deadline</TableCell>
                  <TableCell>Amount</TableCell>
                  <TableCell>Score</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {deadlineSoonGrants.length > 0 ? 
                  deadlineSoonGrants.map(grant => renderGrantRow(grant)) : 
                  <TableRow><TableCell colSpan={6} align="center">No grants due soon matching current criteria.</TableCell></TableRow>}
              </TableBody>
            </Table>
          </TableContainer>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard; 