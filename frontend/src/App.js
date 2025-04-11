import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, CssBaseline } from '@mui/material';
import theme from './theme';

// Layout
import AppLayout from './components/Layout/AppLayout';

// Pages
import Dashboard from './components/Dashboard';

// Placeholder components for routes we'll implement later
const GrantsPage = () => <div>Grants Page</div>;
const SearchPage = () => <div>Search Page</div>;
const SettingsPage = () => <div>Settings Page</div>;
const SavedGrantsPage = () => <div>Saved Grants Page</div>;
const NotFoundPage = () => <div>Page Not Found</div>;

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
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </Router>
    </ThemeProvider>
  );
}

export default App; 