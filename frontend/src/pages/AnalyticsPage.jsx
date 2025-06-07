import { 
    Assessment as AssessmentIcon,
    BarChart as BarChartIcon,
    PieChart as PieChartIcon,
} from '@mui/icons-material';
import { 
    Box, 
    Card, 
    CardContent, 
    Grid, 
    Typography, 
    useTheme 
} from '@mui/material';
import React, { useEffect, useState } from 'react';
import { 
    Bar, 
    BarChart, 
    CartesianGrid, 
    Cell, 
    Legend,
    Pie, 
    PieChart, 
    ResponsiveContainer, 
    Tooltip, 
    XAxis, 
    YAxis 
} from 'recharts';
import { getDistribution } from '../api/apiClient';
import LoaderOverlay from '../components/common/LoaderOverlay';
import EmptyState from '../components/common/EmptyState';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <Card elevation={4} sx={{ p: 1, bgcolor: 'background.paper' }}>
        <Typography variant="subtitle2">{label}</Typography>
        <Typography variant="body2" color="text.secondary">
          Count: {payload[0].value}
        </Typography>
      </Card>
    );
  }
  return null;
};

const AnalyticsPage = () => {
  const theme = useTheme();
  const [loading, setLoading] = useState(true);
  const [distribution, setDistribution] = useState(null);
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const response = await getDistribution();
        const data = response.data || response; // Handle both API response formats
        
        // Transform object data to array format for charts
        const transformedData = {
          categories: data.categories ? Object.entries(data.categories).map(([name, value]) => ({ name, value })) : [],
          deadlines: data.deadlines ? Object.entries(data.deadlines).map(([name, count]) => ({ name, count })) : [],
          scores: data.scores ? Object.entries(data.scores).map(([name, count]) => ({ name, count })) : []
        };
        
        setDistribution(transformedData);
      } catch (e) {
        console.error('Error fetching distribution data:', e);
        setDistribution({ categories: [], deadlines: [], scores: [] });
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const COLORS = [
    theme.palette.primary.main,
    theme.palette.secondary.main,
    theme.palette.info.main,
    theme.palette.success.main,
    theme.palette.warning.main,
    theme.palette.error.main,
    theme.palette.grey[500],
  ];

  return (
    <Box sx={{ p: { xs: 2, sm: 3 } }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <AssessmentIcon sx={{ mr: 2, color: 'primary.main' }} />
        <Typography 
          variant="h4" 
          sx={{ 
            fontWeight: 700,
            fontSize: { xs: '1.5rem', sm: '2rem' }
          }}
        >
          Analytics Dashboard
        </Typography>
      </Box>      <LoaderOverlay loading={loading}>
        {distribution && (distribution.categories.length > 0 || distribution.deadlines.length > 0 || distribution.scores.length > 0) ? (
          <Grid container spacing={3}>
            {/* Categories Chart */}
            {distribution.categories.length > 0 && (
              <Grid item xs={12} md={6}>
                <Card 
                  elevation={0}
                  sx={{ 
                    height: '100%',
                    border: 1,
                    borderColor: 'divider',
                  }}
                >
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      <PieChartIcon sx={{ mr: 1, color: 'text.secondary' }} />
                      <Typography variant="h6">Grant Categories</Typography>
                    </Box>
                    <Box sx={{ height: 300, width: '100%' }}>
                      <ResponsiveContainer>
                        <PieChart>
                          <Pie 
                            data={distribution.categories} 
                            dataKey="value" 
                            nameKey="name" 
                            outerRadius={100}
                            label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                          >
                            {distribution.categories.map((entry, index) => (
                              <Cell 
                                key={`cell-${index}`} 
                                fill={COLORS[index % COLORS.length]}
                                stroke={theme.palette.background.paper}
                                strokeWidth={2}
                              />
                            ))}
                          </Pie>
                          <Tooltip content={<CustomTooltip />} />
                          <Legend />
                        </PieChart>
                      </ResponsiveContainer>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            )}

            {/* Deadlines Chart */}
            {distribution.deadlines.length > 0 && (
              <Grid item xs={12} md={6}>
                <Card 
                  elevation={0}
                  sx={{ 
                    height: '100%',
                    border: 1,
                    borderColor: 'divider',
                  }}
                >
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      <BarChartIcon sx={{ mr: 1, color: 'text.secondary' }} />
                      <Typography variant="h6">Deadlines Distribution</Typography>
                    </Box>
                    <Box sx={{ height: 300, width: '100%' }}>
                      <ResponsiveContainer>
                        <BarChart 
                          data={distribution.deadlines} 
                          margin={{ top: 20, right: 30, left: 0, bottom: 20 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" vertical={false} />
                          <XAxis 
                            dataKey="name" 
                            tick={{ fill: theme.palette.text.secondary }}
                            tickLine={{ stroke: theme.palette.divider }}
                          />
                          <YAxis 
                            tick={{ fill: theme.palette.text.secondary }}
                            tickLine={{ stroke: theme.palette.divider }}
                          />
                          <Tooltip content={<CustomTooltip />} />
                          <Bar 
                            dataKey="count" 
                            fill={theme.palette.primary.main}
                            radius={[4, 4, 0, 0]}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            )}

            {/* Scores Chart */}
            {distribution.scores.length > 0 && (
              <Grid item xs={12} md={6}>
                <Card 
                  elevation={0}
                  sx={{ 
                    height: '100%',
                    border: 1,
                    borderColor: 'divider',
                  }}
                >
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      <BarChartIcon sx={{ mr: 1, color: 'text.secondary' }} />
                      <Typography variant="h6">Relevance Scores</Typography>
                    </Box>
                    <Box sx={{ height: 300, width: '100%' }}>
                      <ResponsiveContainer>
                        <BarChart 
                          data={distribution.scores} 
                          margin={{ top: 20, right: 30, left: 0, bottom: 20 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" vertical={false} />
                          <XAxis 
                            dataKey="name" 
                            tick={{ fill: theme.palette.text.secondary }}
                            tickLine={{ stroke: theme.palette.divider }}
                          />
                          <YAxis 
                            tick={{ fill: theme.palette.text.secondary }}
                            tickLine={{ stroke: theme.palette.divider }}
                          />
                          <Tooltip content={<CustomTooltip />} />
                          <Bar 
                            dataKey="count" 
                            fill={theme.palette.secondary.main}
                            radius={[4, 4, 0, 0]}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            )}
          </Grid>
        ) : (
          <EmptyState 
            message="No analytics data available"
            icon={AssessmentIcon}
          />
        )}
      </LoaderOverlay>
    </Box>
  );
};

export default AnalyticsPage;