import { Box, CircularProgress, Typography } from '@mui/material';
import { useTheme } from '@mui/material/styles';
import React, { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import API from '../api/apiClient';

const AnalyticsPage = () => {
  const theme = useTheme();
  const [loading, setLoading] = useState(true);
  const [distribution, setDistribution] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const data = await API.getDistribution();
        setDistribution(data);
      } catch (e) {
        console.error(e);
        setDistribution({ categories: [], deadlines: [] });
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const COLORS = [theme.palette.primary.main, theme.palette.success.main, theme.palette.info.main, theme.palette.warning.main, theme.palette.error.main];

  if (loading || !distribution) {
    return <Box sx={{display:'flex',justifyContent:'center',mt:4}}><CircularProgress /></Box>;
  }

  return (
    <Box sx={{ p:3 }}>
      <Typography variant="h4" sx={{ mb:3 }}>Analytics</Typography>
      <Box sx={{ height: 300 }}>
        <ResponsiveContainer>
          <PieChart>
            <Pie data={distribution.categories} dataKey="value" nameKey="name" outerRadius={100} label>
              {distribution.categories.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </Box>

      <Box sx={{ height: 300 }}>
        <ResponsiveContainer>
          <BarChart data={distribution.deadlines} margin={{ top: 20 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="count" fill={theme.palette.primary.main} />
          </BarChart>
        </ResponsiveContainer>
      </Box>
    </Box>
  );
};

export default AnalyticsPage; 