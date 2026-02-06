import axios, { AxiosError, AxiosInstance } from 'axios';
import type {
  APIResponse, // Added ApplicationHistory
  ApplicationFeedbackData, // Added ApplicationFeedbackData // Added EnrichedGrant
  ApplicationHistory,
  DashboardStats,
  DistributionData,
  EnrichedGrant,
  // Grant, // Grant is no longer directly used here, EnrichedGrant is used instead
  GrantSearchFilters,
  PaginatedResponse,
  SearchRun,
  UserSettings,
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
  type:
    | 'timeout'
    | 'network'
    | 'auth'
    | 'forbidden'
    | 'not_found'
    | 'server'
    | 'unknown';
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
  },
};

// Create axios instance with base API URL and default headers
const API: AxiosInstance = axios.create({
  baseURL: process.env.REACT_APP_API_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000, // Increased to 15 seconds for slower connections
});

// Attach Bearer token from localStorage on every request
API.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auto-refresh on 401 responses
API.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      localStorage.getItem('refresh_token')
    ) {
      originalRequest._retry = true;
      try {
        const refreshRes = await axios.post(
          `${API.defaults.baseURL}/auth/refresh`,
          { refresh_token: localStorage.getItem('refresh_token') }
        );
        const newToken = refreshRes.data.access_token;
        localStorage.setItem('access_token', newToken);
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return API(originalRequest);
      } catch {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

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
    type: 'unknown' as const,
  });

  if (axiosError.code === 'ECONNABORTED') {
    enhancedError.type = 'timeout';
    enhancedError.message =
      'Request timed out. Please check your connection and try again.';
  } else if (!axiosError.response) {
    enhancedError.type = 'network';
    enhancedError.message = 'Network error. Please check your connection.';
  } else if (axiosError.response.status === 401) {
    enhancedError.type = 'auth';
    enhancedError.message = 'Session expired. Please login again.';
  } else if (axiosError.response.status === 403) {
    enhancedError.type = 'forbidden';
    enhancedError.message =
      'You do not have permission to perform this action.';
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
export const getDashboardStats = async (): Promise<
  APIResponse<DashboardStats>
> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.get<APIResponse<DashboardStats>>(
      '/dashboard/stats'
    );
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

export const getDistribution = async (): Promise<
  APIResponse<DistributionData>
> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.get<APIResponse<DistributionData>>(
      '/analytics/distribution'
    );
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

// Grants endpoints
export const getGrants = async (
  params: Partial<GrantSearchFilters> = {}
): Promise<PaginatedResponse<EnrichedGrant>> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.get<PaginatedResponse<EnrichedGrant>>(
      '/grants',
      { params }
    );
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

export const searchGrants = async (
  filters: GrantSearchFilters
): Promise<PaginatedResponse<EnrichedGrant>> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.post<PaginatedResponse<EnrichedGrant>>(
      '/grants/search',
      filters
    );
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

export const getGrantById = async (
  id: string
): Promise<APIResponse<EnrichedGrant>> => {
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

export const getSavedGrants = async (): Promise<
  PaginatedResponse<EnrichedGrant>
> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.get<PaginatedResponse<EnrichedGrant>>(
      '/grants/saved'
    );
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

export const updateUserSettings = async (
  settings: Partial<UserSettings>
): Promise<APIResponse<UserSettings>> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.put<APIResponse<UserSettings>>(
      '/user/settings',
      settings
    );
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

export const getLastRun = async (): Promise<
  APIResponse<{ timestamp: string; status: string }>
> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.get<
      APIResponse<{ timestamp: string; status: string }>
    >('/system/last-run');
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

export const getRunHistory = async (): Promise<
  APIResponse<Array<{ timestamp: string; status: string; results: number }>>
> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.get<
      APIResponse<Array<{ timestamp: string; status: string; results: number }>>
    >('/system/run-history');
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

// Application History and Feedback Endpoints
export const submitApplicationFeedback = async (
  feedbackData: ApplicationFeedbackData
): Promise<APIResponse<ApplicationHistory>> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.post<APIResponse<ApplicationHistory>>(
      '/applications/feedback',
      feedbackData
    );
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

export const getApplicationHistoryForGrant = async (
  grantId: string
): Promise<PaginatedResponse<ApplicationHistory>> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.get<PaginatedResponse<ApplicationHistory>>(
      `/applications/history`,
      { params: { grant_id: grantId } }
    );
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

export const getAllApplicationHistory = async (
  params: { page?: number; pageSize?: number; grant_id?: string } = {}
): Promise<PaginatedResponse<ApplicationHistory>> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.get<PaginatedResponse<ApplicationHistory>>(
      '/applications/history',
      { params }
    );
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

// Search Run Management
export const getSearchRuns = async (
  params: {
    page?: number;
    page_size?: number;
    run_type?: string;
    status?: string;
    days_back?: number;
  } = {}
): Promise<{
  items: SearchRun[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
  has_prev: boolean;
}> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.get<{
      items: SearchRun[];
      total: number;
      page: number;
      page_size: number;
      has_next: boolean;
      has_prev: boolean;
    }>('/search-runs', { params });
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

export const getLatestAutomatedRun = async (): Promise<{
  status: string;
  health: string;
  data: SearchRun | null;
  message: string;
}> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.get<{
      status: string;
      health: string;
      data: SearchRun | null;
      message: string;
    }>('/search-runs/latest-automated');
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

export const getSearchRunStatistics = async (
  days_back: number = 7
): Promise<{
  status: string;
  data: {
    total_runs: number;
    successful_runs: number;
    failed_runs: number;
    success_rate: number;
    average_grants_found: number;
    average_duration_seconds: number;
    days_analyzed: number;
  };
  generated_at: string;
}> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.get<{
      status: string;
      data: {
        total_runs: number;
        successful_runs: number;
        failed_runs: number;
        success_rate: number;
        average_grants_found: number;
        average_duration_seconds: number;
        days_analyzed: number;
      };
      generated_at: string;
    }>('/search-runs/statistics', { params: { days_back } });
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

export const createManualSearchRun = async (
  searchQuery?: string,
  searchFilters?: Record<string, any>
): Promise<{
  status: string;
  message: string;
  data: {
    id: number;
    timestamp: string;
    run_type: string;
    status: string;
  };
}> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.post<{
      status: string;
      message: string;
      data: {
        id: number;
        timestamp: string;
        run_type: string;
        status: string;
      };
    }>('/search-runs', {
      search_query: searchQuery,
      search_filters: searchFilters,
    });
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

export const getSearchRunDetails = async (
  runId: number
): Promise<{
  status: string;
  data: SearchRun;
}> => {
  if (circuitBreaker.isOpen()) {
    throw new Error('Service temporarily unavailable');
  }
  try {
    const response = await API.get<{
      status: string;
      data: SearchRun;
    }>(`/search-runs/${runId}`);
    circuitBreaker.reset();
    return response.data;
  } catch (error) {
    circuitBreaker.recordFailure();
    throw categorizeError(error);
  }
};

// Business Profile endpoints
export const getBusinessProfile = async (): Promise<any> => {
  try {
    const response = await API.get('/business-profile');
    return response.data;
  } catch (error) {
    throw categorizeError(error);
  }
};

export const updateBusinessProfile = async (profile: any): Promise<any> => {
  try {
    const response = await API.put('/business-profile', profile);
    return response.data;
  } catch (error) {
    throw categorizeError(error);
  }
};

export const getDocuments = async (): Promise<any> => {
  try {
    const response = await API.get('/business-profile/documents');
    return response.data;
  } catch (error) {
    throw categorizeError(error);
  }
};

export const uploadDocuments = async (files: File[]): Promise<any> => {
  try {
    const formData = new FormData();
    files.forEach(file => formData.append('file', file));
    const response = await API.post('/business-profile/documents', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  } catch (error) {
    throw categorizeError(error);
  }
};

export const deleteDocument = async (docId: string): Promise<any> => {
  try {
    const response = await API.delete(`/business-profile/documents/${docId}`);
    return response.data;
  } catch (error) {
    throw categorizeError(error);
  }
};

// Application endpoints
export const getApplications = async (params: any = {}): Promise<any> => {
  try {
    const response = await API.get('/applications', { params });
    return response.data;
  } catch (error) {
    throw categorizeError(error);
  }
};

export const generateApplication = async (grantId: string): Promise<any> => {
  try {
    const response = await API.post('/applications/generate', { grant_id: grantId });
    return response.data;
  } catch (error) {
    throw categorizeError(error);
  }
};

export const getApplicationById = async (id: string): Promise<any> => {
  try {
    const response = await API.get(`/applications/${id}`);
    return response.data;
  } catch (error) {
    throw categorizeError(error);
  }
};

// Subscription endpoints
export const getCurrentSubscription = async (): Promise<any> => {
  try {
    const response = await API.get('/subscriptions/current');
    return response.data;
  } catch (error) {
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
  getAllApplicationHistory, // Added new method
  getSearchRuns, // Added new method
  getLatestAutomatedRun, // Added new method
  getSearchRunStatistics, // Added new method
  createManualSearchRun, // Added new method
  getSearchRunDetails, // Added new method
  getBusinessProfile,
  updateBusinessProfile,
  getDocuments,
  uploadDocuments,
  deleteDocument,
  getApplications,
  generateApplication,
  getApplicationById,
  getCurrentSubscription,
};

export default APIWithMethods;
