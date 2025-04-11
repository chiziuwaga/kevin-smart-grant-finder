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
  // Grants
  getGrants: (params) => apiClient.get('/grants', { params }),
  getGrantById: (id) => apiClient.get(`/grants/${id}`),
  searchGrants: (query) => apiClient.get('/grants/search', { params: { query } }),
  
  // User settings
  getUserSettings: () => apiClient.get('/user/settings'),
  updateUserSettings: (settings) => apiClient.put('/user/settings', settings),
  
  // Saved grants
  getSavedGrants: () => apiClient.get('/user/saved-grants'),
  saveGrant: (grantId) => apiClient.post(`/user/saved-grants/${grantId}`),
  unsaveGrant: (grantId) => apiClient.delete(`/user/saved-grants/${grantId}`),
  
  // Dashboard data
  getDashboardStats: () => apiClient.get('/dashboard/stats'),
  getRecentGrants: () => apiClient.get('/dashboard/recent-grants'),
  getHighPriorityGrants: () => apiClient.get('/dashboard/high-priority'),
  
  // Notifications
  getNotificationHistory: () => apiClient.get('/notifications/history'),
  testNotification: (channel) => apiClient.post('/notifications/test', { channel }),
  
  // System status
  getSystemStatus: () => apiClient.get('/system/status'),
};

export default API; 