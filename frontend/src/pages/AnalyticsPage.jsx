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
import '../styles/swiss-theme.css';

const COLORS = ['#1a1a1a', '#E53935', '#1976D2', '#43A047', '#FDD835', '#9e9e9e'];

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="card" style={{ padding: 'var(--space-1)' }}>
        <p style={{ margin: 0, fontWeight: '600' }}>{label}</p>
        <p style={{ margin: 0, fontSize: 'var(--font-size-sm)', color: 'var(--color-gray-600)' }}>
          Count: {payload[0].value}
        </p>
      </div>
    );
  }
  return null;
};

const AnalyticsPage = () => {
  const [loading, setLoading] = useState(true);
  const [distribution, setDistribution] = useState(null);
  const [message, setMessage] = useState({ text: '', type: '' });

  const showMessage = (text, type) => {
    setMessage({ text, type });
    setTimeout(() => setMessage({ text: '', type: '' }), 3000);
  };

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const response = await getDistribution();
        const data = response.data || response;

        // Transform object data to array format for charts
        const transformedData = {
          categories: data.categories ? Object.entries(data.categories).map(([name, value]) => ({ name, value })) : [],
          deadlines: data.deadlines ? Object.entries(data.deadlines).map(([name, count]) => ({ name, count })) : [],
          scores: data.scores ? Object.entries(data.scores).map(([name, count]) => ({ name, count })) : []
        };

        setDistribution(transformedData);
      } catch (e) {
        console.error('Error fetching distribution data:', e);
        showMessage('Failed to load analytics data', 'error');
        setDistribution({ categories: [], deadlines: [], scores: [] });
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p className="mt-2">Loading analytics...</p>
      </div>
    );
  }

  const hasData = distribution && (
    distribution.categories.length > 0 ||
    distribution.deadlines.length > 0 ||
    distribution.scores.length > 0
  );

  return (
    <div className="container" style={{ padding: 'var(--space-3)' }}>
      <div className="flex items-center mb-3">
        <span style={{ fontSize: '2rem', marginRight: 'var(--space-2)' }}>📊</span>
        <h1>Analytics Dashboard</h1>
      </div>

      {message.text && (
        <div className={`alert alert-${message.type} mb-3`}>
          {message.text}
        </div>
      )}

      {hasData ? (
        <div className="grid grid-cols-1 gap-3">
          {/* Categories Distribution */}
          {distribution.categories.length > 0 && (
            <div className="card">
              <div className="flex items-center mb-3">
                <span style={{ fontSize: '1.5rem', marginRight: 'var(--space-1)' }}>🏷️</span>
                <h2>Grants by Category</h2>
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={distribution.categories}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    label={(entry) => `${entry.name}: ${entry.value}`}
                  >
                    {distribution.categories.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Deadlines Distribution */}
          {distribution.deadlines.length > 0 && (
            <div className="card">
              <div className="flex items-center mb-3">
                <span style={{ fontSize: '1.5rem', marginRight: 'var(--space-1)' }}>📅</span>
                <h2>Grants by Deadline Range</h2>
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={distribution.deadlines}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                  <XAxis dataKey="name" stroke="#1a1a1a" />
                  <YAxis stroke="#1a1a1a" />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="count" fill="#1a1a1a" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Scores Distribution */}
          {distribution.scores.length > 0 && (
            <div className="card">
              <div className="flex items-center mb-3">
                <span style={{ fontSize: '1.5rem', marginRight: 'var(--space-1)' }}>⭐</span>
                <h2>Grants by Relevance Score</h2>
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={distribution.scores}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                  <XAxis dataKey="name" stroke="#1a1a1a" />
                  <YAxis stroke="#1a1a1a" />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="count" fill="#1976D2" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      ) : (
        <div className="empty-state">
          <div style={{ fontSize: '3rem', marginBottom: 'var(--space-2)' }}>📊</div>
          <p>No analytics data available</p>
          <p className="text-secondary text-sm">
            Start searching for grants to see analytics
          </p>
        </div>
      )}
    </div>
  );
};

export default AnalyticsPage;
