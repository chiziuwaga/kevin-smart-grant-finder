import { CssBaseline, ThemeProvider } from '@mui/material';
import React from 'react';
import { Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import theme from './theme';

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
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
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
    </ThemeProvider>
  );
}

export default App; 