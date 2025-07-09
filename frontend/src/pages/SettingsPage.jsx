import {
  History as HistoryIcon,
  Notifications as NotificationsIcon,
  Save as SaveIcon,
  Schedule as ScheduleIcon,
  Settings as SettingsIcon,
  Computer as SystemIcon,
} from '@mui/icons-material';
import {
  Box,
  Button,
  Card,
  CardContent,
  FormControl,
  FormControlLabel,
  Grid,
  InputLabel,
  MenuItem,
  Select,
  Switch,
  Tab,
  Tabs,
  TextField,
  Typography,
} from '@mui/material';
import { useSnackbar } from 'notistack';
import { useEffect, useState } from 'react';
import API from '../api/apiClient';
import LoaderOverlay from '../components/common/LoaderOverlay';
import CronJobStatus from '../components/CronJobStatus';
import SearchHistory from '../components/SearchHistory';

const SCHEDULE_OPTIONS = [
    { value: 'Mon/Thu', label: 'Twice a week (Monday & Thursday)' },
    { value: 'daily', label: 'Daily' },
    { value: 'weekly', label: 'Weekly (Monday)' },
];

const SettingsPage = () => {
  const { enqueueSnackbar } = useSnackbar();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [currentTab, setCurrentTab] = useState(0);
  const [settings, setSettings] = useState({
    alerts: {
      sms: false,
      telegram: false,
      email: false,
      phone: '',
      emailAddress: '',
    },
    schedule: 'Mon/Thu',
    minRelevanceScore: 70,
  });
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const data = await API.getUserSettings();
        setSettings(prev => ({
          ...prev,
          ...data,
        }));
      } catch (e) {
        console.error(e);
        enqueueSnackbar('Failed to load settings', { variant: 'error' });
      } finally {
        setLoading(false);
      }
    };
    fetchSettings();
  }, [enqueueSnackbar]);

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
      enqueueSnackbar('Settings saved successfully', { variant: 'success' });
      setHasChanges(false);
    } catch (e) {
      console.error(e);
      enqueueSnackbar('Failed to save settings', { variant: 'error' });
    } finally {
      setSaving(false);
    }
  };

  // Tab panel component
  const TabPanel = ({ children, value, index, ...other }) => {
    return (
      <div
        role="tabpanel"
        hidden={value !== index}
        id={`settings-tabpanel-${index}`}
        aria-labelledby={`settings-tab-${index}`}
        {...other}
      >
        {value === index && (
          <Box sx={{ py: 3 }}>
            {children}
          </Box>
        )}
      </div>
    );
  };

  return (
    <Box sx={{ p: { xs: 2, sm: 3 } }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <SettingsIcon sx={{ mr: 2, color: 'primary.main' }} />
        <Typography 
          variant="h4" 
          sx={{ 
            fontWeight: 700,
            fontSize: { xs: '1.5rem', sm: '2rem' }
          }}
        >
          Settings
        </Typography>
      </Box>

      {/* Tabs Navigation */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
        <Tabs 
          value={currentTab} 
          onChange={(event, newValue) => setCurrentTab(newValue)}
          aria-label="settings tabs"
        >
          <Tab 
            icon={<NotificationsIcon />} 
            label="Notifications" 
            id="settings-tab-0"
            aria-controls="settings-tabpanel-0"
          />
          <Tab 
            icon={<ScheduleIcon />} 
            label="Schedule" 
            id="settings-tab-1"
            aria-controls="settings-tabpanel-1"
          />
          <Tab 
            icon={<HistoryIcon />} 
            label="Search History" 
            id="settings-tab-2"
            aria-controls="settings-tabpanel-2"
          />
          <Tab 
            icon={<SystemIcon />} 
            label="System Status" 
            id="settings-tab-3"
            aria-controls="settings-tabpanel-3"
          />
        </Tabs>
      </Box>

      <LoaderOverlay loading={loading}>
        {/* Notifications Tab */}
        <TabPanel value={currentTab} index={0}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Card 
                elevation={0}
                sx={{ 
                  height: '100%',
                  border: 1,
                  borderColor: 'divider',
                }}
              >
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                    <NotificationsIcon sx={{ mr: 1, color: 'text.secondary' }} />
                    <Typography variant="h6">Email Notifications</Typography>
                  </Box>

                  <Box sx={{ mb: 3 }}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={settings.alerts.email}
                          onChange={handleChange('alerts', 'email')}
                          color="primary"
                        />
                      }
                      label="Email Notifications"
                    />
                    {settings.alerts.email && (
                      <TextField
                        fullWidth
                        label="Email Address"
                        value={settings.alerts.emailAddress || ''}
                        onChange={handleChange('alerts', 'emailAddress')}
                        sx={{ mt: 1 }}
                        size="small"
                      />
                    )}
                  </Box>

                  <Box sx={{ mb: 3 }}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={settings.alerts.telegram}
                          onChange={handleChange('alerts', 'telegram')}
                          color="primary"
                        />
                      }
                      label="Telegram Notifications"
                    />
                  </Box>

                  <Box sx={{ mb: 3 }}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={settings.alerts.sms}
                          onChange={handleChange('alerts', 'sms')}
                          color="primary"
                        />
                      }
                      label="SMS Notifications"
                    />
                    {settings.alerts.sms && (
                      <TextField
                        fullWidth
                        label="Phone Number"
                        value={settings.alerts.phone || ''}
                        onChange={handleChange('alerts', 'phone')}
                        placeholder="+1 (555) 123-4567"
                        sx={{ mt: 1 }}
                        size="small"
                      />
                    )}
                  </Box>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={6}>
              <Card 
                elevation={0}
                sx={{ 
                  height: '100%',
                  border: 1,
                  borderColor: 'divider',
                }}
              >
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                    <SettingsIcon sx={{ mr: 1, color: 'text.secondary' }} />
                    <Typography variant="h6">Relevance Threshold</Typography>
                  </Box>

                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Only grants with a relevance score above this threshold will trigger notifications.
                  </Typography>

                  <TextField
                    fullWidth
                    type="number"
                    label="Minimum Relevance Score"
                    value={settings.minRelevanceScore}
                    onChange={handleChange('minRelevanceScore')}
                    inputProps={{ min: 0, max: 100 }}
                    helperText="Score between 0-100"
                  />
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Save Button for Notifications Tab */}
          {hasChanges && (
            <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
              <Button
                variant="contained"
                onClick={handleSave}
                disabled={saving}
                startIcon={<SaveIcon />}
              >
                {saving ? 'Saving...' : 'Save Settings'}
              </Button>
            </Box>
          )}
        </TabPanel>

        {/* Schedule Tab */}
        <TabPanel value={currentTab} index={1}>
          <Card 
            elevation={0}
            sx={{ 
              border: 1,
              borderColor: 'divider',
            }}
          >
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                <ScheduleIcon sx={{ mr: 1, color: 'text.secondary' }} />
                <Typography variant="h6">Search Schedule</Typography>
              </Box>

              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Configure when automated grant searches should run.
              </Typography>

              <FormControl fullWidth sx={{ mb: 3 }}>
                <InputLabel>Schedule Frequency</InputLabel>
                <Select
                  value={settings.schedule}
                  onChange={handleChange('schedule')}
                  label="Schedule Frequency"
                >
                  {SCHEDULE_OPTIONS.map(option => (
                    <MenuItem key={option.value} value={option.value}>
                      {option.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {/* Save Button for Schedule Tab */}
              {hasChanges && (
                <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <Button
                    variant="contained"
                    onClick={handleSave}
                    disabled={saving}
                    startIcon={<SaveIcon />}
                  >
                    {saving ? 'Saving...' : 'Save Settings'}
                  </Button>
                </Box>
              )}
            </CardContent>
          </Card>
        </TabPanel>

        {/* Search History Tab */}
        <TabPanel value={currentTab} index={2}>
          <SearchHistory />
        </TabPanel>

        {/* System Status Tab */}
        <TabPanel value={currentTab} index={3}>
          <CronJobStatus />
        </TabPanel>
      </LoaderOverlay>
    </Box>
  );
};

export default SettingsPage;