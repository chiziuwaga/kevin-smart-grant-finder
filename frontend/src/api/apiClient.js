import axios from 'axios';

// Create axios instance with base API URL and default headers
const API = axios.create({
  baseURL: process.env.REACT_APP_API_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000, // 10 second timeout
  // Add retry configuration
  retry: 3,
  retryDelay: (retryCount) => {
    return retryCount * 1000; // time interval between retries
  }
});

// Add retry logic
API.interceptors.response.use(undefined, async (err) => {
  const { config } = err;
  if (!config || !config.retry) {
    return Promise.reject(err);
  }
  
  config.__retryCount = config.__retryCount || 0;
  
  if (config.__retryCount >= config.retry) {
    return Promise.reject(err);
  }
  
  config.__retryCount += 1;
  
  // Create new promise to handle retry
  const backoff = new Promise((resolve) => {
    setTimeout(() => {
      resolve();
    }, config.retryDelay(config.__retryCount));
  });
  
  // Return promise that retries the request
  await backoff;
  return API(config);
});

// Add response interceptor for error handling
API.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', {
      url: error.config?.url,
      method: error.config?.method,
      status: error.response?.status,
      data: error.response?.data,
      message: error.message
    });

    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('authOK');
      window.location.reload();
      return Promise.reject(new Error('Session expired. Please login again.'));
    }

    // Convert axios error to more user-friendly format
    const enhancedError = new Error(
      error.response?.data?.message || 
      error.response?.data?.detail ||
      error.message ||
      'An unexpected error occurred'
    );
    enhancedError.status = error.response?.status;
    enhancedError.data = error.response?.data;
    return Promise.reject(enhancedError);
  }
);

// Dashboard endpoints
export const getDashboardStats = () => API.get('/dashboard/stats');
export const getDistribution = () => API.get('/analytics/distribution');

// Grants endpoints
export const getGrants = (params = {}) => API.get('/grants', { params });
export const searchGrants = (filters = {}) => API.post('/grants/search', filters);
export const getGrantById = (id) => API.get(`/grants/${id}`);
export const getSavedGrants = () => API.get('/grants/saved');
export const saveGrant = (id) => API.post(`/grants/${id}/save`);
export const unsaveGrant = (id) => API.delete(`/grants/${id}/save`);

// System endpoints
export const runSearch = () => API.post('/system/run-search');
export const getLastRun = () => API.get('/system/last-run');
export const getRunHistory = () => API.get('/system/run-history');

// User settings
export const getUserSettings = () => API.get('/user/settings');
export const updateUserSettings = (settings) => API.put('/user/settings', settings);

export default API;