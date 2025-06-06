import React, { createContext, useContext, useRef, useState, useCallback } from 'react';
import { Backdrop, CircularProgress, Snackbar, Alert } from '@mui/material';

const LoadingContext = createContext();

export function LoadingProvider({ children }) {
  const loadingRef = useRef(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const errorTimeoutRef = useRef(null);

  const startLoading = useCallback(() => {
    loadingRef.current += 1;
    setIsLoading(true);
  }, []);

  const stopLoading = useCallback(() => {
    loadingRef.current = Math.max(0, loadingRef.current - 1);
    if (loadingRef.current === 0) {
      setIsLoading(false);
    }
  }, []);

  const showError = useCallback((message, duration = 6000) => {
    setError(message);
    if (errorTimeoutRef.current) {
      clearTimeout(errorTimeoutRef.current);
    }
    errorTimeoutRef.current = setTimeout(() => {
      setError(null);
    }, duration);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
    if (errorTimeoutRef.current) {
      clearTimeout(errorTimeoutRef.current);
      errorTimeoutRef.current = null;
    }
  }, []);

  // Reset loading state if it's been active too long (failsafe)
  React.useEffect(() => {
    let timeoutId;
    if (isLoading) {
      timeoutId = setTimeout(() => {
        console.warn('Loading state timeout - resetting');
        loadingRef.current = 0;
        setIsLoading(false);
        showError('Operation timed out. Please try again.');
      }, 30000); // 30 second timeout
    }
    return () => timeoutId && clearTimeout(timeoutId);
  }, [isLoading, showError]);

  // Cleanup on unmount
  React.useEffect(() => {
    return () => {
      if (errorTimeoutRef.current) {
        clearTimeout(errorTimeoutRef.current);
      }
    };
  }, []);

  const value = React.useMemo(() => ({
    isLoading,
    startLoading,
    stopLoading,
    showError,
    clearError
  }), [isLoading, startLoading, stopLoading, showError, clearError]);

  return (
    <LoadingContext.Provider value={value}>
      {children}
      <Backdrop
        sx={{ 
          color: '#fff', 
          zIndex: (theme) => theme.zIndex.drawer + 1,
          flexDirection: 'column',
          gap: 2 
        }}
        open={isLoading}
      >
        <CircularProgress color="inherit" />
        {isLoading && loadingRef.current > 1 && (
          <div>{`Processing ${loadingRef.current} requests...`}</div>
        )}
      </Backdrop>
      <Snackbar
        open={!!error}
        autoHideDuration={6000}
        onClose={clearError}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={clearError} severity="error" sx={{ width: '100%' }}>
          {error}
        </Alert>
      </Snackbar>
    </LoadingContext.Provider>
  );
}

export const useLoading = () => {
  const context = useContext(LoadingContext);
  if (!context) {
    throw new Error('useLoading must be used within a LoadingProvider');
  }
  return context;
};
