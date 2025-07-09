# 🚨 Grant Search Alerts & History Implementation Plan

## **Overview**

This document outlines the implementation plan for user-facing grant search alerts and search history monitoring to provide transparency and immediate feedback when grant searches fail (both manual and automated).

## **Current System Status**

### ✅ **Already Implemented (Backend)**

- `SearchRun` model with comprehensive error tracking
- `/search-runs/live-status/{run_id}` - Real-time search status API
- `/search-runs/analytics` - Search performance analytics
- `/system/scheduler-status` - Cron job health monitoring
- `SearchStatusMonitor.jsx` - Real-time status component
- Error handling in `run_full_search_cycle`

### 🔧 **Needs Implementation**

- Integration of alerts into user workflow
- Settings page search history tab
- Cron job status widget
- User-friendly error recovery actions
- Comprehensive search history dashboard

---

## **Feature 1: User-Facing Search Failure Alerts**

### **1.1 Enhanced Error Notifications**

**Location**: Frontend components and pages that trigger searches

**Implementation**:

1. **Immediate Toast Notifications**: When searches fail, show contextual error messages
2. **Persistent Error Banners**: For critical failures that need user attention
3. **Recovery Action Buttons**: Provide specific actions users can take

```jsx
// Example implementation in SearchPage.jsx
const handleSearchError = (error, searchRunId) => {
  // Show immediate notification
  enqueueSnackbar(`Search failed: ${getErrorMessage(error)}`, {
    variant: 'error',
    persist: true,
    action: (
      <Box>
        <Button onClick={() => retrySearch()} color="inherit">
          Retry
        </Button>
        <Button onClick={() => openErrorDetails(searchRunId)} color="inherit">
          Details
        </Button>
      </Box>
    ),
  });
};
```

### **1.2 Error Context & Recovery Actions**

**Specific Error Types & User Actions**:

- **API Rate Limits**: "Rate limit exceeded. Retrying in 5 minutes..."
- **Service Unavailable**: "External service temporarily down. Try again shortly."
- **Authentication Errors**: "Please check API credentials in Settings."
- **Network Issues**: "Connection problem. Check your internet and retry."
- **Configuration Errors**: "System configuration issue. Contact support."

### **1.3 Real-time Search Monitoring Integration**

**Current Status**: `SearchStatusMonitor.jsx` exists but needs integration

**Implementation Steps**:

1. Integrate monitor into search-triggering pages
2. Show progress bars and current step information
3. Provide cancel/stop functionality for long-running searches

---

## **Feature 2: Heroku Scheduler Monitoring**

### **2.1 Cron Job Health Dashboard**

**Backend Status**: `/system/scheduler-status` endpoint exists

**Frontend Implementation**:

```jsx
// New component: CronJobStatus.jsx
const CronJobStatus = () => {
  // Poll scheduler status every 30 seconds
  // Show:
  // - Last automated run status
  // - Next expected run time
  // - Success rate over past week
  // - Any scheduler issues
};
```

### **2.2 Automated Run Failure Alerts**

**Implementation**:

1. **Dashboard Widget**: Show cron job health on main dashboard
2. **Email/SMS Alerts**: For critical cron job failures (future enhancement)
3. **Telegram Notifications**: Already integrated, enhance for cron failures

### **2.3 Manual Trigger Capability**

**Enhancement**: Add "Run Search Now" button that:

- Triggers manual search via `/system/run-search`
- Shows real-time progress via `SearchStatusMonitor`
- Provides immediate feedback on success/failure

---

## **Feature 3: Search History Dashboard**

### **3.1 Settings Page Integration**

**Current Status**: Settings page exists, needs history sub-tab

**Implementation**: Add new tab to existing settings with:

- Search run timeline
- Filter by run type (manual/automated)
- Filter by status (success/failed/partial)
- Export functionality

### **3.2 Search History Components**

#### **A. SearchHistoryTable Component**

```jsx
const SearchHistoryTable = () => {
  // Features:
  // - Paginated table of all search runs
  // - Sort by date, status, grants found
  // - Filter by run type and date range
  // - Click for detailed view
  // - Retry failed searches
};
```

#### **B. SearchRunDetail Component**

```jsx
const SearchRunDetail = ({ runId }) => {
  // Features:
  // - Complete search run information
  // - Error details and logs
  // - Grants found in that run
  // - Performance metrics
  // - Retry option for failed runs
};
```

#### **C. SearchAnalytics Component**

```jsx
const SearchAnalytics = () => {
  // Features:
  // - Success rate charts
  // - Average grants found trends
  // - Performance over time
  // - Error frequency analysis
};
```

---

## **Implementation Timeline**

### **Phase 1: Enhanced Error Alerts (Priority: High)**

1. ✅ Backend error tracking (Done)
2. 🔧 Frontend error notification enhancement
3. 🔧 Recovery action implementation
4. 🔧 SearchStatusMonitor integration

### **Phase 2: Search History Dashboard (Priority: High)**

1. 🔧 Settings page tab addition
2. 🔧 SearchHistoryTable component
3. 🔧 SearchRunDetail component
4. 🔧 Search analytics integration

### **Phase 3: Cron Job Monitoring (Priority: Medium)**

1. ✅ Backend scheduler status (Done)
2. 🔧 CronJobStatus widget
3. 🔧 Dashboard integration
4. 🔧 Manual trigger enhancement

### **Phase 4: Advanced Features (Priority: Low)**

1. 🔧 Export search history
2. 🔧 Advanced analytics charts
3. 🔧 Automated failure notifications
4. 🔧 Search scheduling configuration

---

## **User Experience Flow**

### **Scenario 1: Manual Search Fails**

1. User initiates search on Search page
2. SearchStatusMonitor shows real-time progress
3. Search fails → Immediate toast notification with error + retry button
4. User can click "Details" to see full error information
5. User can retry immediately or check Settings > History for details

### **Scenario 2: Automated Search Fails**

1. Cron job fails during automated run
2. Dashboard shows cron job health warning
3. Settings > History shows failed run details
4. User can manually trigger new search
5. System provides specific error context and recovery steps

### **Scenario 3: User Reviews Search History**

1. User navigates to Settings > Search History
2. Sees timeline of all search runs (manual + automated)
3. Can filter by date range, status, run type
4. Click on any run for detailed view
5. Can retry failed searches directly from history

---

## **Technical Considerations**

### **API Integration**

- ✅ `/search-runs/live-status/{run_id}` - Real-time status
- ✅ `/search-runs/analytics` - Performance metrics
- ✅ `/system/scheduler-status` - Cron job health
- 🔧 Enhance error handling in existing endpoints

### **State Management**

- Use React hooks for local component state
- Consider context for global search status
- Cache search history data appropriately

### **Performance**

- Paginate search history results
- Implement efficient polling for real-time status
- Lazy load detailed search run information

### **Error Handling**

- Graceful degradation when APIs are unavailable
- Retry mechanisms with exponential backoff
- Clear user messaging for all error scenarios

---

## **Success Metrics**

### **User Experience**

- ✅ Users immediately know when searches fail
- ✅ Users understand why searches failed
- ✅ Users can easily retry failed searches
- ✅ Users can monitor automated search health

### **Technical Reliability**

- ✅ All search failures are logged and trackable
- ✅ Cron job health is monitored and visible
- ✅ System provides actionable error recovery
- ✅ Search history is comprehensive and searchable

---

## **Next Steps**

1. **Start with Phase 1**: Enhance error notifications in existing search pages
2. **Integrate SearchStatusMonitor**: Into SearchPage and Dashboard
3. **Build Search History Tab**: Add to Settings page with basic table
4. **Add Cron Monitoring**: Create dashboard widget for scheduler status
5. **Polish & Test**: Comprehensive testing of all error scenarios

This implementation will provide users with full transparency into grant search operations and immediate feedback when issues occur, significantly improving the user experience and system reliability.
