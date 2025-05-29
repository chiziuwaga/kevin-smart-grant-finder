import axios from 'axios';
import type { 
  Grant, 
  GrantSearchFilters,
  DashboardStats, 
  DistributionData,
  UserSettings,
  APIResponse,
  PaginatedResponse
} from './types';

// Circuit breaker implementation
const circuitBreaker = {
  failures: 0,
  lastFailure: null as number | null,
  threshold: 5,
  resetTimeout: 60000,
  
  recordFailure() {
    this.failures++;
    this.lastFailure = Date.now();
  },
  
  isOpen() {
    if (this.failures >= this.threshold && this.lastFailure) {
      const timeSinceLastFailure = Date.now() - this.lastFailure;
      if (timeSinceLastFailure < this.resetTimeout) {
        return true;
      }
      this.reset();
    }
    return false;
  },
  
  reset() {
    this.failures = 0;
    this.lastFailure = null;
  }
};

// Create axios instance with base API URL and default headers
const API = axios.create({
  baseURL: process.env.REACT_APP_API_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000, // Increased to 15 seconds for slower connections
  retry: 3,
  retryDelay: (retryCount) => {
    return Math.min(1000 * Math.pow(2, retryCount), 10000); // Exponential backoff capped at 10s
  }
});

// Error categorization helper
function categorizeError(error: any): Error {
  const enhancedError = new Error(
    error.response?.data?.message || 
    error.response?.data?.detail ||
    error.message ||
    'An unexpected error occurred'
  );
  
  (enhancedError as any).status = error.response?.status;
  (enhancedError as any).data = error.response?.data;
  
  if (error.code === 'ECONNABORTED') {
    (enhancedError as any).type = 'timeout';
    enhancedError.message = 'Request timed out. Please check your connection and try again.';
  } else if (!error.response) {
    (enhancedError as any).type = 'network';
    enhancedError.message = 'Network error. Please check your connection.';
  } else if (error.response.status === 401) {
    (enhancedError as any).type = 'auth';
    enhancedError.message = 'Session expired. Please login again.';
    localStorage.removeItem('authOK');
    window.location.reload();
  } else if (error.response.status === 403) {
    (enhancedError as any).type = 'forbidden';
    enhancedError.message = 'You do not have permission to perform this action.';
  } else if (error.response.status === 404) {
    (enhancedError as any).type = 'not_found';
    enhancedError.message = 'The requested resource was not found.';
  } else if (error.response.status >= 500) {
    (enhancedError as any).type = 'server';
    enhancedError.message = 'Server error. Please try again later.';
  }

  return enhancedError;
}

// Dashboard endpoints
export const getDashboardStats = async (): Promise<APIResponse<DashboardStats>> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.get<APIResponse<DashboardStats>>('/dashboard/stats');
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

export const getDistribution = async (): Promise<APIResponse<DistributionData>> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.get<APIResponse<DistributionData>>('/analytics/distribution');
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

// Grants endpoints
export const getGrants = async (params: Partial<GrantSearchFilters> = {}): Promise<PaginatedResponse<Grant>> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.get<PaginatedResponse<Grant>>('/grants', { params });
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

export const searchGrants = async (filters: GrantSearchFilters): Promise<PaginatedResponse<Grant>> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.post<PaginatedResponse<Grant>>('/grants/search', filters);
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

export const getGrantById = async (id: string): Promise<APIResponse<Grant>> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.get<APIResponse<Grant>>(`/grants/${id}`);
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

export const getSavedGrants = async (): Promise<PaginatedResponse<Grant>> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.get<PaginatedResponse<Grant>>('/grants/saved');
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

export const saveGrant = async (id: string): Promise<APIResponse<void>> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.post<APIResponse<void>>(`/grants/${id}/save`);
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

export const unsaveGrant = async (id: string): Promise<APIResponse<void>> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.delete<APIResponse<void>>(`/grants/${id}/save`);
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

// User settings endpoints
export const getUserSettings = async (): Promise<APIResponse<UserSettings>> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.get<APIResponse<UserSettings>>('/user/settings');
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

export const updateUserSettings = async (settings: Partial<UserSettings>): Promise<APIResponse<UserSettings>> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.put<APIResponse<UserSettings>>('/user/settings', settings);
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

// System endpoints
export const runSearch = async (): Promise<APIResponse<void>> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.post<APIResponse<void>>('/system/run-search');
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

// Add named exports to default export to support both import styles
const APIWithMethods = {
  ...API,
  getDashboardStats,
  getDistribution,
  getGrants,
  searchGrants,
  getGrantById,
  getSavedGrants,
  saveGrant,
  unsaveGrant,
  runSearch,
  getUserSettings,
  updateUserSettings
};

export default APIWithMethods;
