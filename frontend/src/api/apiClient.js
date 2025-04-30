import axios from 'axios';

// Decide base URL dynamically – in Vercel we proxy `/api/*`, in local dev we hit localhost:8000 directly.
const baseURL = process.env.REACT_APP_API_URL ||
  (window.location.hostname === 'localhost' ? 'http://localhost:8000/api' : '/api');

const apiClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Helper to unwrap .data to reduce boilerplate
const unwrap = promise => promise.then(res => res.data);

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
  // ----- Dashboard & Overview -----
  getOverview: () => unwrap(apiClient.get('/grants/overview')),

  // ----- Grant queries -----
  getGrants: params => unwrap(apiClient.get('/grants/search', { params })), // simple GET wrapper
  searchGrants: body => unwrap(apiClient.post('/grants/search', body)),     // advanced search POST

  // ----- Saved grants -----
  getSavedGrants: () => unwrap(apiClient.get('/user/saved-grants')),
  saveGrant: id => unwrap(apiClient.post(`/user/saved-grants/${id}`)),
  unsaveGrant: id => unwrap(apiClient.delete(`/user/saved-grants/${id}`)),

  // ----- Analytics -----
  getDistribution: () => unwrap(apiClient.get('/analytics/distribution')),

  // ----- User settings (placeholders) -----
  getUserSettings: () => Promise.resolve({ alerts: { sms: true, telegram: true }, schedule: 'Mon/Thu' }),
  updateUserSettings: data => Promise.resolve(data),
};

export default API; 