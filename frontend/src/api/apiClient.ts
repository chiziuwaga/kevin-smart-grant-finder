import axios, { AxiosInstance, AxiosError } from 'axios';
import type { 
  // Grant, // Grant is no longer directly used here, EnrichedGrant is used instead
  GrantSearchFilters,
  DashboardStats, 
  DistributionData,
  UserSettings,
  APIResponse,
  PaginatedResponse,
  EnrichedGrant, // Added EnrichedGrant
  ApplicationHistory, // Added ApplicationHistory
  ApplicationFeedbackData // Added ApplicationFeedbackData
} from './types';

interface CircuitBreaker {
  failures: number;
  lastFailure: number | null;
  threshold: number;
  resetTimeout: number;
  recordFailure(): void;
  isOpen(): boolean;
  reset(): void;
}

interface EnhancedError extends Error {
  status?: number;
  data?: any;
  type: 'timeout' | 'network' | 'auth' | 'forbidden' | 'not_found' | 'server' | 'unknown';
}

interface ErrorResponseData {
  message?: string;
  detail?: string;
}

// Circuit breaker implementation
const circuitBreaker: CircuitBreaker = {
  failures: 0,
  lastFailure: null,
  threshold: 5,
  resetTimeout: 60000,
  
  recordFailure() {
    this.failures++;
    this.lastFailure = Date.now();
  },
  
  isOpen(): boolean {
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
const API: AxiosInstance = axios.create({
  baseURL: process.env.REACT_APP_API_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000 // Increased to 15 seconds for slower connections
});

// Error categorization helper
function categorizeError(error: AxiosError | Error): EnhancedError {
  const axiosError = error as AxiosError<ErrorResponseData>;
  const enhancedError = new Error(
    axiosError.response?.data?.message || 
    axiosError.response?.data?.detail ||
    error.message ||
    'An unexpected error occurred'
  ) as EnhancedError;
  
  Object.assign(enhancedError, {
    status: axiosError.response?.status,
    data: axiosError.response?.data,
    type: 'unknown' as const
  });
  
  if (axiosError.code === 'ECONNABORTED') {
    enhancedError.type = 'timeout';
    enhancedError.message = 'Request timed out. Please check your connection and try again.';
  } else if (!axiosError.response) {
    enhancedError.type = 'network';
    enhancedError.message = 'Network error. Please check your connection.';
  } else if (axiosError.response.status === 401) {
    enhancedError.type = 'auth';
    enhancedError.message = 'Session expired. Please login again.';
  } else if (axiosError.response.status === 403) {
    enhancedError.type = 'forbidden';
    enhancedError.message = 'You do not have permission to perform this action.';
  } else if (axiosError.response.status === 404) {
    enhancedError.type = 'not_found';
    enhancedError.message = 'The requested resource was not found.';
  } else if (axiosError.response.status >= 500) {
    enhancedError.type = 'server';
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
export const getGrants = async (params: Partial<GrantSearchFilters> = {}): Promise<PaginatedResponse<EnrichedGrant>> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.get<PaginatedResponse<EnrichedGrant>>('/grants', { params });
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

export const searchGrants = async (filters: GrantSearchFilters): Promise<PaginatedResponse<EnrichedGrant>> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.post<PaginatedResponse<EnrichedGrant>>('/grants/search', filters);
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

export const getGrantById = async (id: string): Promise<APIResponse<EnrichedGrant>> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.get<APIResponse<EnrichedGrant>>(`/grants/${id}`);
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

export const getSavedGrants = async (): Promise<PaginatedResponse<EnrichedGrant>> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.get<PaginatedResponse<EnrichedGrant>>('/grants/saved');
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

export const getLastRun = async (): Promise<APIResponse<{ timestamp: string; status: string }>> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.get<APIResponse<{ timestamp: string; status: string }>>('/system/last-run');
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

export const getRunHistory = async (): Promise<APIResponse<Array<{ timestamp: string; status: string; results: number }>>> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.get<APIResponse<Array<{ timestamp: string; status: string; results: number }>>>('/system/run-history');
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

// Application History and Feedback Endpoints
export const submitApplicationFeedback = async (feedbackData: ApplicationFeedbackData): Promise<APIResponse<ApplicationHistory>> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.post<APIResponse<ApplicationHistory>>('/applications/feedback', feedbackData);
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

export const getApplicationHistoryForGrant = async (grantId: string): Promise<PaginatedResponse<ApplicationHistory>> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.get<PaginatedResponse<ApplicationHistory>>(`/applications/history`, { params: { grant_id: grantId } });
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

export const getAllApplicationHistory = async (params: { page?: number, pageSize?: number, grant_id?: string } = {}): Promise<PaginatedResponse<ApplicationHistory>> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.get<PaginatedResponse<ApplicationHistory>>('/applications/history', { params });
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
  getLastRun,
  getRunHistory,
  getUserSettings,
  updateUserSettings,
  submitApplicationFeedback, // Added new method
  getApplicationHistoryForGrant, // Added new method
  getAllApplicationHistory // Added new method
};

export default APIWithMethods;
