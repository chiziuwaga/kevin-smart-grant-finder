// Grant related types
export interface Grant {
  id: string;
  title: string;
  description: string;
  funding_amount?: number; // This might be deprecated in favor of funding_amount_display in EnrichedGrant
  deadline?: string;
  eligibility_criteria?: string; // This might be deprecated in favor of eligibility_summary_llm in EnrichedGrant
  category?: string;
  source_url?: string;
  source_name?: string;
  score?: number; // This might be deprecated in favor of overall_composite_score in EnrichedGrant
  // Fields from old Grant model that might still be in use or for fallback
  relevanceScore?: number; // Example: if overall_composite_score is not yet populated
  fundingAmount?: string | number; // Fallback for funding_amount_display
}

export interface ResearchScores {
  sector_relevance_score?: number;
  geographic_relevance_score?: number;
  operational_alignment_score?: number;
}

export interface ComplianceScores {
  business_logic_alignment_score?: number;
  feasibility_score?: number;
  strategic_synergy_score?: number;
}

export interface EnrichedGrant
  extends Omit<Grant, 'score' | 'funding_amount' | 'eligibility_criteria'> {
  grant_id: string; // Assuming this is the primary ID, aliasing from 'id' if necessary
  summary_llm?: string;
  eligibility_summary_llm?: string;
  research_scores?: ResearchScores;
  compliance_scores?: ComplianceScores;
  overall_composite_score?: number;
  identified_sector?: string;
  keywords?: string[];
  categories_project?: string[];
  funder_name?: string;
  application_open_date?: string;
  funding_amount_min?: number;
  funding_amount_max?: number;
  funding_amount_exact?: number;
  funding_amount_display?: string; // Pre-formatted funding string
  // Retain some original Grant fields for compatibility or direct use
  deadline_date?: string; // Potentially more specific than just 'deadline'
  is_saved?: boolean; // If the grant is saved by the user
}

export interface GrantSearchFilters {
  minScore?: number;
  category?: string;
  deadlineBefore?: string;
  searchText?: string;
}

// Dashboard related types
export interface DashboardStats {
  totalGrants: number;
  averageScore: number;
  grantsThisMonth: number;
  upcomingDeadlines: number;
}

export interface DistributionData {
  categories: { [key: string]: number };
  deadlines: { [key: string]: number };
  scores: { [key: string]: number };
}

// User settings types
export interface UserSettings {
  emailNotifications: boolean;
  deadlineReminders: boolean;
  searchFrequency: 'daily' | 'weekly' | 'monthly';
  categories: string[];
  minimumScore: number;
}

// API response types
export interface APIResponse<T> {
  data: T;
  status: 'success' | 'error';
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

// Application History and Feedback Types
export interface ApplicationFeedbackData {
  grant_id: string;
  submission_date: string; // ISO date string
  status:
    | 'Draft'
    | 'Submitted'
    | 'Under Review'
    | 'Awarded'
    | 'Rejected'
    | 'Withdrawn'
    | 'Other';
  outcome_notes?: string;
  feedback_for_profile_update?: string;
  // Optional fields based on schema
  application_id?: string; // If an ID is assigned upon submission by our system
  status_reason?: string;
  is_successful_outcome?: boolean;
}

export interface ApplicationHistory extends ApplicationFeedbackData {
  id: string; // Primary key for the history entry
  created_at: string; // ISO date string
  updated_at: string; // ISO date string
  // Potentially link back to the user if multi-user system in future
  // user_id?: string;
}

// Search Run types
export interface SearchRun {
  id: number;
  timestamp: string;
  created_at: string;
  run_type: 'automated' | 'manual' | 'scheduled';
  status: 'success' | 'failed' | 'partial' | 'in_progress';
  grants_found: number;
  high_priority: number;
  duration_seconds?: number;
  search_query?: string;
  search_filters?: Record<string, any>;
  error_message?: string;
  error_details?: Record<string, any>;
  user_triggered: boolean;
  sources_searched?: number;
  api_calls_made?: number;
  processing_time_ms?: number;
}

export interface SearchRunStatistics {
  total_runs: number;
  successful_runs: number;
  failed_runs: number;
  success_rate: number;
  average_grants_found: number;
  average_duration_seconds: number;
  days_analyzed: number;
}

// Enhanced error types for search alerts
export interface SearchError {
  type:
    | 'timeout'
    | 'network'
    | 'auth'
    | 'forbidden'
    | 'not_found'
    | 'server'
    | 'unknown';
  message: string;
  details?: Record<string, any>;
  status?: number;
  timestamp: string;
  search_context?: {
    query?: string;
    filters?: Record<string, any>;
    source?: string;
  };
}
