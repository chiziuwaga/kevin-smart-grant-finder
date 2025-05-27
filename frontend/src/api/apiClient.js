import axios from 'axios';

// Create axios instance with base API URL and default headers
const API = axios.create({
  baseURL: process.env.REACT_APP_API_URL || '/api', // Use environment variable or fallback
  headers: {
    'Content-Type': 'application/json',
  },
});

// Dashboard endpoints
export const getDashboardStats = () => API.get('/dashboard/stats');  // Changed from /grants/overview
export const getDistribution = () => API.get('/analytics/distribution');

// Grants endpoints
export const getGrants = (params = {}) => API.get('/grants', { params });  // Use for filtered queries
export const searchGrants = (filters = {}) => API.post('/grants/search', filters);  // Use for advanced search
export const getGrantById = (id) => API.get(`/grants/${id}`);

// System endpoints
export const runSearch = () => API.post('/system/run-search');
export const getLastRun = () => API.get('/system/last-run');
export const getRunHistory = () => API.get('/system/run-history');

// User settings
export const getUserSettings = () => API.get('/user/settings');
export const updateUserSettings = (settings) => API.put('/user/settings', settings);

// Handle errors globally
API.interceptors.response.use(
  (response) => response,
  (error) => {
    // Log errors
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// Export the API instance as default while keeping named exports
export default API;