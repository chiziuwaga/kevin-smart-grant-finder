import React, { createContext, useContext, useState, useRef } from 'react';
import { Backdrop, CircularProgress } from '@mui/material';

const LoadingContext = createContext({
  isLoading: false,
  setLoading: () => {},
  withLoading: async () => {},
});

export const useLoading = () => useContext(LoadingContext);

export const LoadingProvider = ({ children }) => {
  const [isLoading, setIsLoading] = useState(false);
  const countRef = useRef(0);

  const setLoading = (loading) => {
    countRef.current = loading ? countRef.current + 1 : Math.max(0, countRef.current - 1);
    setIsLoading(countRef.current > 0);
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
