import axios from 'axios';

// Create an axios instance with base configuration
const apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds timeout
});

// Request interceptor for API calls
apiClient.interceptors.request.use(
  (config) => {
    // You can set auth tokens here from localStorage if needed
    // const token = localStorage.getItem('authToken');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for API calls
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Handle 401 errors, potentially refresh token or redirect to login
      // window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// API endpoints
const API = {
  // Grants API (FastAPI backend)
  searchGrants: (params) => apiClient.get('/search', { params }),
  
  // Placeholder endpoints for future features (currently NOP)
  getUserSettings: () => Promise.resolve({ data: {} }),
  updateUserSettings: () => Promise.resolve({}),
  
  // Saved grants placeholders
  getSavedGrants: () => apiClient.get('/user/saved-grants'),
  saveGrant: (grantId) => apiClient.post(`/user/saved-grants/${grantId}`),
  unsaveGrant: (grantId) => apiClient.delete(`/user/saved-grants/${grantId}`),
  
  // Dashboard data using metrics endpoint
  getDashboardStats: () => apiClient.get('/dashboard/stats'),
  getRecentGrants: () => apiClient.get('/search', { params: { category: 'recent' } }),
  getHighPriorityGrants: () => apiClient.get('/search', { params: { category: 'high_priority' } }),
  
  // Notifications placeholders
  getNotificationHistory: () => Promise.resolve({ data: [] }),
  testNotification: () => Promise.resolve({}),
  
  // System status from metrics
  getSystemStatus: () => apiClient.get('/metrics'),
};

export default API; 