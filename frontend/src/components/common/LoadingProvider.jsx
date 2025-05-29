import React, { createContext, useContext, useState } from 'react';
import { Backdrop, CircularProgress } from '@mui/material';

const LoadingContext = createContext({
  isLoading: false,
  setLoading: () => {},
  withLoading: async () => {},
});

export const useLoading = () => useContext(LoadingContext);

export const LoadingProvider = ({ children }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [loadingCount, setLoadingCount] = useState(0);

  const setLoading = (loading) => {
    setLoadingCount(prev => {
      const next = loading ? prev + 1 : prev - 1;
      setIsLoading(next > 0);
      return next;
    });
  };

  const withLoading = async (callback) => {
    setLoading(true);
    try {
      return await callback();
    } finally {
      setLoading(false);
    }
  };

  return (
    <LoadingContext.Provider value={{ isLoading, setLoading, withLoading }}>
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
      </Backdrop>
    </LoadingContext.Provider>
  );
};
