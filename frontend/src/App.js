import { CssBaseline, ThemeProvider } from '@mui/material';
import React, { useState, useEffect } from 'react';
import { Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import theme from './theme';
import ErrorBoundary from './components/common/ErrorBoundary';
import { LoadingProvider } from './components/common/LoadingProvider';

// Layout
import AppLayout from './components/Layout/AppLayout';

// Pages
import Dashboard from './components/Dashboard';
import AnalyticsPage from './pages/AnalyticsPage';
import GrantsPage from './pages/GrantsPage';
import NotFoundPage from './pages/NotFoundPage';
import SavedGrantsPage from './pages/SavedGrantsPage';
import SearchPage from './pages/SearchPage';
import SettingsPage from './pages/SettingsPage';

function App() {
  const [ok, setOk] = useState(() => localStorage.getItem('authOK') === '1');
  const [apiError, setApiError] = useState(false);

  // Check API health on startup
  useEffect(() => {
    const checkApiHealth = async () => {
      try {
        const response = await fetch(process.env.REACT_APP_API_URL + '/health');
        if (!response.ok) throw new Error('API health check failed');
        setApiError(false);
      } catch (error) {
        console.error('API health check failed:', error);
        setApiError(true);
      }
    };
    
    checkApiHealth();
    const interval = setInterval(checkApiHealth, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, []);

  if (!ok) {
    const pwd = prompt('Enter password to access Smart Grant Finder');
    if (pwd === 'smartgrantfinder') {
      localStorage.setItem('authOK', '1');
      setOk(true);
    } else {
      window.location.href = 'https://google.com';
    }
    return null;
  }

  if (apiError) {
    return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          padding: '20px',
          textAlign: 'center'
        }}>
          <h1>API Connection Error</h1>
          <p>Unable to connect to the backend API. Please try again later or contact support.</p>
          <button onClick={() => window.location.reload()}>
            Retry Connection
          </button>
        </div>
      </ThemeProvider>
    );
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <ErrorBoundary>
        <LoadingProvider>
          <Router>
            <Routes>
              <Route path="/" element={<AppLayout />}>
                <Route index element={<Dashboard />} />
                <Route path="grants" element={<GrantsPage />} />
                <Route path="search" element={<SearchPage />} />
                <Route path="saved" element={<SavedGrantsPage />} />
                <Route path="settings" element={<SettingsPage />} />
                <Route path="analytics" element={<AnalyticsPage />} />
                <Route path="*" element={<NotFoundPage />} />
              </Route>
            </Routes>
          </Router>
        </LoadingProvider>
      </ErrorBoundary>
    </ThemeProvider>
  );
}

export default App;