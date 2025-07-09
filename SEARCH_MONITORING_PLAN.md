# 🎯 Grant Search Alerts & History Tracking - Implementation Plan

## **Executive Summary**

Implementing comprehensive search monitoring and history tracking to provide users with transparency into grant search operations, including failure alerts and automated run monitoring.

---

## **Feature 1: Grant Search Failure Alerts**

### **Backend Enhancements**

#### 1.1 Enhanced Search Status API

```python
# New endpoint: /api/search-runs/live-status/{run_id}
@api_router.get("/search-runs/live-status/{run_id}")
async def get_search_run_live_status(run_id: int, db: AsyncSession):
    """Get real-time status of a running search with detailed progress"""
    # Returns: status, progress_percentage, current_step, error_info
```

#### 1.2 Search Failure Notification System

```python
# Enhanced error handling in run_full_search_cycle
async def run_full_search_cycle_with_notifications():
    """Enhanced version with user notifications for failures"""
    # - Capture detailed error context
    # - Send immediate notifications for failures
    # - Provide actionable recovery suggestions
```

#### 1.3 API Error Classification

```python
class SearchErrorType(str, PyEnum):
    API_RATE_LIMIT = "api_rate_limit"
    SERVICE_UNAVAILABLE = "service_unavailable"
    AUTHENTICATION_ERROR = "authentication_error"
    CONFIGURATION_ERROR = "configuration_error"
    NETWORK_ERROR = "network_error"
    DATA_PROCESSING_ERROR = "data_processing_error"
```

### **Frontend Implementation**

#### 1.4 Real-time Search Monitoring

```jsx
// New component: SearchStatusMonitor.jsx
const SearchStatusMonitor = ({ searchRunId }) => {
  // - Polls search status every 2 seconds
  // - Shows progress bar and current step
  // - Displays immediate error alerts
  // - Provides retry and help actions
};
```

#### 1.5 Enhanced Toast Notifications

```jsx
// Enhanced notification system with error context
const showSearchError = (error, context) => {
  enqueueSnackbar(
    `Search failed: ${error.message}. ${getRecoveryAction(error.type)}`,
    {
      variant: 'error',
      action: <RetryButton />,
      persist: true,
    }
  );
};
```

---

## **Feature 2: Search History Dashboard**

### **Backend Enhancements**

#### 2.1 Enhanced Search Run Queries

```python
# Extended filtering capabilities
@api_router.get("/search-runs/detailed")
async def get_detailed_search_runs(
    page: int = 1,
    page_size: int = 20,
    run_type: Optional[str] = None,  # "automated", "manual", "scheduled"
    status: Optional[str] = None,    # "success", "failed", "partial"
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    include_metrics: bool = True,
    db: AsyncSession = Depends(get_db_session)
):
    """Get comprehensive search run history with filtering and metrics"""
```

#### 2.2 Search Run Analytics

```python
@api_router.get("/search-runs/analytics")
async def get_search_analytics(
    days_back: int = 30,
    db: AsyncSession = Depends(get_db_session)
):
    """Get search performance analytics and trends"""
    # Returns:
    # - Success rate trends
    # - Average grants found per run
    # - Performance metrics
    # - Error frequency analysis
```

### **Frontend Implementation**

#### 2.3 Settings Page - Search History Subtab

```jsx
// Enhanced SettingsPage.jsx with new tab
const SettingsPage = () => {
  const [activeTab, setActiveTab] = useState('general');

  const tabs = [
    { id: 'general', label: 'General Settings' },
    { id: 'notifications', label: 'Notifications' },
    { id: 'search-history', label: 'Search History' }, // NEW TAB
  ];

  return (
    <Container>
      <TabContext value={activeTab}>
        <TabList>
          {tabs.map((tab) => (
            <Tab key={tab.id} label={tab.label} />
          ))}
        </TabList>

        <TabPanel value="general">
          <GeneralSettings />
        </TabPanel>
        <TabPanel value="notifications">
          <NotificationSettings />
        </TabPanel>
        <TabPanel value="search-history">
          <SearchHistory />
        </TabPanel>
      </TabContext>
    </Container>
  );
};
```

#### 2.4 Search History Component

```jsx
// New component: SearchHistory.jsx
const SearchHistory = () => {
  // Features:
  // - Interactive timeline of search runs
  // - Filtering by type, status, date range
  // - Expandable run details
  // - Performance metrics charts
  // - Retry failed searches
  // - Export history to CSV
};
```

#### 2.5 Search Run Card Component

```jsx
// New component: SearchRunCard.jsx
const SearchRunCard = ({ run, expanded, onToggle }) => {
  return (
    <Card>
      <CardHeader>
        <RunStatusChip status={run.status} />
        <Typography>{formatRunType(run.run_type)}</Typography>
        <Typography variant="caption">
          {formatDateTime(run.timestamp)}
        </Typography>
      </CardHeader>

      {expanded && (
        <CardContent>
          <SearchRunDetails run={run} />
          <SearchRunMetrics run={run} />
          {run.status === 'failed' && (
            <ErrorAnalysis error={run.error_details} />
          )}
        </CardContent>
      )}
    </Card>
  );
};
```

---

## **Feature 3: Cron Job Monitoring**

### **Backend Implementation**

#### 3.1 Heroku Scheduler Health Check

```python
@api_router.get("/system/scheduler-status")
async def get_scheduler_status(db: AsyncSession = Depends(get_db_session)):
    """Check Heroku scheduler status and last automated run health"""
    # Returns:
    # - Last scheduled run timestamp
    # - Scheduler health status
    # - Next expected run time
    # - Any configuration issues
```

#### 3.2 Automated Run Failure Detection

```python
async def check_automated_run_health():
    """Monitor automated runs and alert on failures or delays"""
    # - Check if automated runs are running on schedule
    # - Detect prolonged failures
    # - Send admin notifications for system issues
```

### **Frontend Implementation**

#### 3.3 Cron Job Status Widget

```jsx
// Component for Settings > Search History
const CronJobStatus = () => {
  return (
    <Paper>
      <Typography variant="h6">Automated Search Status</Typography>
      <Box>
        <StatusIndicator status={cronStatus} />
        <Typography>Last Run: {lastRunTime}</Typography>
        <Typography>Next Run: {nextRunTime}</Typography>
        <Typography>Success Rate: {successRate}%</Typography>
      </Box>
      {hasIssues && (
        <Alert severity="warning">Configuration issues detected</Alert>
      )}
    </Paper>
  );
};
```

---

## **Implementation Priority & Timeline**

### **Phase 1: Immediate Search Feedback (Day 1-2)**

1. ✅ Enhanced error handling in existing search endpoints
2. ✅ Frontend toast notifications for search failures
3. ✅ Basic retry mechanism for failed searches

### **Phase 2: History Dashboard (Day 3-4)**

1. ✅ New Settings page subtab
2. ✅ Search run history component
3. ✅ Basic filtering and display

### **Phase 3: Advanced Monitoring (Day 5-6)**

1. ✅ Cron job status monitoring
2. ✅ Performance analytics
3. ✅ Automated failure detection

### **Phase 4: Polish & Testing (Day 7)**

1. ✅ User experience refinements
2. ✅ Error message improvements
3. ✅ Comprehensive testing

---

## **Success Metrics**

### **User Experience**

- ✅ Users receive immediate feedback on search failures
- ✅ Clear visibility into system health and performance
- ✅ Easy access to search history and troubleshooting

### **System Reliability**

- ✅ Faster detection and resolution of search issues
- ✅ Improved monitoring of automated processes
- ✅ Better error reporting and analysis

### **Technical Quality**

- ✅ Comprehensive error tracking and logging
- ✅ Scalable monitoring infrastructure
- ✅ User-friendly error messages and recovery actions

---

## **Technical Specifications**

### **Database Changes**

- ✅ Enhanced SearchRun model (already exists with needed fields)
- ✅ New error classification enum
- ✅ Performance metrics tracking

### **API Endpoints**

- ✅ `/search-runs/live-status/{run_id}` - Real-time search status
- ✅ `/search-runs/detailed` - Enhanced history with filtering
- ✅ `/search-runs/analytics` - Performance analytics
- ✅ `/system/scheduler-status` - Cron job health check

### **Frontend Components**

- ✅ `SearchStatusMonitor.jsx` - Real-time status tracking
- ✅ `SearchHistory.jsx` - History dashboard
- ✅ `SearchRunCard.jsx` - Individual run details
- ✅ `CronJobStatus.jsx` - Automated run monitoring
- ✅ Enhanced Settings page with new tab

---

## **Implementation Notes**

### **Error Recovery Actions**

```jsx
const getRecoveryAction = (errorType) => {
  switch (errorType) {
    case 'api_rate_limit':
      return 'Try again in a few minutes when rate limits reset.';
    case 'service_unavailable':
      return "External service is down. We'll retry automatically.";
    case 'authentication_error':
      return 'Please check your API credentials in settings.';
    default:
      return 'Please try again or contact support if the issue persists.';
  }
};
```

### **Performance Considerations**

- ✅ Efficient pagination for search history
- ✅ Caching for frequently accessed data
- ✅ Real-time updates without overwhelming the server
- ✅ Progressive loading for large datasets

This implementation provides comprehensive visibility into grant search operations while maintaining excellent user experience and system performance.
