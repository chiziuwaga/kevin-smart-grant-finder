// Grant related types
export interface Grant {
    id: string;
    title: string;
    description: string;
    funding_amount?: number;
    deadline?: string;
    eligibility_criteria?: string;
    category?: string;
    source_url?: string;
    source_name?: string;
    score?: number;
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
    telegramEnabled: boolean;
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
