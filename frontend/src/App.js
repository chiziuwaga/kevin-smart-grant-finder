import React, { useEffect, useState } from 'react';
import { Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import ErrorBoundary from './components/common/ErrorBoundary';
import { LoadingProvider } from './components/common/LoadingProvider';
import Auth0ProviderWithHistory from './components/Auth/Auth0Provider';
import ProtectedRoute from './components/Auth/ProtectedRoute';

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
import ApplicationsPage from './pages/ApplicationsPage';
import BusinessProfilePage from './pages/BusinessProfilePage';

// Swiss Design System CSS
import './styles/swiss-theme.css';

function App() {
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

  if (apiError) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        padding: '20px',
        textAlign: 'center',
        fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'
      }}>
        <h1 style={{ marginBottom: '16px' }}>API Connection Error</h1>
        <p style={{ marginBottom: '24px', color: '#666666' }}>
          Unable to connect to the backend API. Please try again later or contact support.
        </p>
        <button
          onClick={() => window.location.reload()}
          className="btn btn-primary"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <LoadingProvider>
        <Router>
          <Auth0ProviderWithHistory>
            <Routes>
              <Route
                path="/*"
                element={
                  <ProtectedRoute>
                    <AppLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<Dashboard />} />
                <Route path="grants" element={<GrantsPage />} />
                <Route path="search" element={<SearchPage />} />
                <Route path="saved" element={<SavedGrantsPage />} />
                <Route path="applications" element={<ApplicationsPage />} />
                <Route path="profile" element={<BusinessProfilePage />} />
                <Route path="settings" element={<SettingsPage />} />
                <Route path="analytics" element={<AnalyticsPage />} />
                <Route path="*" element={<NotFoundPage />} />
              </Route>
            </Routes>
          </Auth0ProviderWithHistory>
        </Router>
      </LoadingProvider>
    </ErrorBoundary>
  );
}

export default App;
