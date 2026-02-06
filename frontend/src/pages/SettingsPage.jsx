import { useEffect, useState } from 'react';
import API from '../api/apiClient';
import CronJobStatus from '../components/CronJobStatus';
import SearchHistoryTab from '../components/SearchHistoryTab';
import ManualSearchTrigger from '../components/ManualSearchTrigger';
import '../styles/swiss-theme.css';

const SCHEDULE_OPTIONS = [
  { value: 'Mon/Thu', label: 'Twice a week (Monday & Thursday)' },
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly (Monday)' },
];

const SettingsPage = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [currentTab, setCurrentTab] = useState(0);
  const [message, setMessage] = useState({ text: '', type: '' });
  const [settings, setSettings] = useState({
    alerts: {
      sms: false,
      email: false,
      phone: '',
      emailAddress: '',
    },
    schedule: 'Mon/Thu',
    minRelevanceScore: 70,
  });
  const [hasChanges, setHasChanges] = useState(false);
  const [subscription, setSubscription] = useState({
    plan: 'free',
    status: 'active',
    usage: {
      searches: 0,
      maxSearches: 10,
      applications: 0,
      maxApplications: 5,
    },
  });

  const showMessage = (text, type) => {
    setMessage({ text, type });
    setTimeout(() => setMessage({ text: '', type: '' }), 3000);
  };

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const data = await API.getUserSettings();
        setSettings(prev => ({ ...prev, ...data }));
      } catch (e) {
        console.error(e);
        showMessage('Failed to load settings', 'error');
      } finally {
        setLoading(false);
      }
    };
    const fetchSubscription = async () => {
      try {
        const data = await API.getCurrentSubscription();
        if (data) {
          setSubscription({
            plan: data.plan || data.plan_name || 'free',
            status: data.status || 'active',
            usage: {
              searches: data.usage?.searches ?? data.searches_used ?? 0,
              maxSearches: data.usage?.maxSearches ?? data.searches_limit ?? 10,
              applications: data.usage?.applications ?? data.applications_used ?? 0,
              maxApplications: data.usage?.maxApplications ?? data.applications_limit ?? 5,
            },
          });
        }
      } catch (e) {
        console.error('Subscription not available:', e);
      }
    };
    fetchSettings();
    fetchSubscription();
  }, []);

  const handleChange = (section, key) => (event) => {
    const value = event.target.type === 'checkbox' ? event.target.checked : event.target.value;
    setSettings(prev => ({
      ...prev,
      [section]: typeof key === 'undefined' ? value : {
        ...prev[section],
        [key]: value,
      },
    }));
    setHasChanges(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await API.updateUserSettings(settings);
      showMessage('Settings saved successfully', 'success');
      setHasChanges(false);
    } catch (e) {
      console.error(e);
      showMessage('Failed to save settings', 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p className="mt-2">Loading settings...</p>
      </div>
    );
  }

  return (
    <div className="container" style={{ padding: 'var(--space-3)' }}>
      <h1 className="mb-3">Settings</h1>

      {message.text && (
        <div className={`alert alert-${message.type} mb-3`}>
          {message.text}
        </div>
      )}

      <div className="tabs">
        <button
          className={`tab ${currentTab === 0 ? 'active' : ''}`}
          onClick={() => setCurrentTab(0)}
        >
          💳 Subscription
        </button>
        <button
          className={`tab ${currentTab === 1 ? 'active' : ''}`}
          onClick={() => setCurrentTab(1)}
        >
          🔔 Alerts
        </button>
        <button
          className={`tab ${currentTab === 2 ? 'active' : ''}`}
          onClick={() => setCurrentTab(2)}
        >
          ⚙️ System
        </button>
        <button
          className={`tab ${currentTab === 3 ? 'active' : ''}`}
          onClick={() => setCurrentTab(3)}
        >
          📜 History
        </button>
      </div>

      {/* Tab 0: Subscription */}
      {currentTab === 0 && (
        <div className="card">
          <h2>Subscription & Usage</h2>
          <div style={{ marginBottom: 'var(--space-3)' }}>
            <div className="flex justify-between items-center mb-2">
              <span>Plan: <strong className="text-uppercase">{subscription.plan}</strong></span>
              <span className={`chip chip-${subscription.status === 'active' ? 'success' : 'error'}`}>
                {subscription.status}
              </span>
            </div>
          </div>

          <div style={{ marginBottom: 'var(--space-3)' }}>
            <h3>Usage Limits</h3>
            <div style={{ marginBottom: 'var(--space-2)' }}>
              <div className="flex justify-between mb-1">
                <span className="text-sm">Searches</span>
                <span className="text-sm">
                  {subscription.usage.searches} / {subscription.usage.maxSearches}
                </span>
              </div>
              <div className="progress">
                <div
                  className="progress-bar"
                  style={{ width: `${(subscription.usage.searches / subscription.usage.maxSearches) * 100}%` }}
                ></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-1">
                <span className="text-sm">Applications Generated</span>
                <span className="text-sm">
                  {subscription.usage.applications} / {subscription.usage.maxApplications}
                </span>
              </div>
              <div className="progress">
                <div
                  className="progress-bar"
                  style={{ width: `${(subscription.usage.applications / subscription.usage.maxApplications) * 100}%` }}
                ></div>
              </div>
            </div>
          </div>

          <button
            className="btn btn-primary"
            onClick={() => showMessage('Stripe billing coming soon. Contact support to upgrade.', 'info')}
          >
            💳 Upgrade Plan
          </button>
        </div>
      )}

      {/* Tab 1: Alerts */}
      {currentTab === 1 && (
        <div className="card">
          <h2>Alert Preferences</h2>

          <div className="form-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={settings.alerts.email}
                onChange={handleChange('alerts', 'email')}
              />
              <span>Email Notifications</span>
            </label>
          </div>

          {settings.alerts.email && (
            <div className="form-group">
              <label className="label">Email Address</label>
              <input
                type="email"
                className="input"
                value={settings.alerts.emailAddress}
                onChange={handleChange('alerts', 'emailAddress')}
                placeholder="your.email@example.com"
              />
            </div>
          )}

          <div className="form-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={settings.alerts.sms}
                onChange={handleChange('alerts', 'sms')}
              />
              <span>SMS Notifications</span>
            </label>
          </div>

          {settings.alerts.sms && (
            <div className="form-group">
              <label className="label">Phone Number</label>
              <input
                type="tel"
                className="input"
                value={settings.alerts.phone}
                onChange={handleChange('alerts', 'phone')}
                placeholder="+1 (555) 123-4567"
              />
            </div>
          )}

          <div className="form-group">
            <label className="label">Search Schedule</label>
            <select
              className="input"
              value={settings.schedule}
              onChange={handleChange('schedule')}
            >
              {SCHEDULE_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="label">Minimum Relevance Score: {settings.minRelevanceScore}%</label>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={settings.minRelevanceScore}
              onChange={handleChange('minRelevanceScore')}
              style={{ width: '100%' }}
            />
          </div>

          {hasChanges && (
            <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? 'Saving...' : '💾 Save Changes'}
            </button>
          )}
        </div>
      )}

      {/* Tab 2: System */}
      {currentTab === 2 && (
        <div className="card">
          <h2>System Settings</h2>

          <div className="mb-4">
            <h3>Cron Job Status</h3>
            <CronJobStatus />
          </div>

          <div className="divider"></div>

          <div className="mb-4">
            <h3>Manual Search Trigger</h3>
            <ManualSearchTrigger />
          </div>
        </div>
      )}

      {/* Tab 3: History */}
      {currentTab === 3 && (
        <div className="card">
          <h2>Search History</h2>
          <SearchHistoryTab />
        </div>
      )}
    </div>
  );
};

export default SettingsPage;
