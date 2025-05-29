import {
    Settings as SettingsIcon,
    Notifications as NotificationsIcon,
    Schedule as ScheduleIcon,
    Save as SaveIcon,
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
    TextField,
    Typography,
} from '@mui/material';
import { useSnackbar } from 'notistack';
import React, { useEffect, useState } from 'react';
import API from '../api/apiClient';
import LoaderOverlay from '../components/common/LoaderOverlay';

const SCHEDULE_OPTIONS = [
    { value: 'Mon/Thu', label: 'Twice a week (Monday & Thursday)' },
    { value: 'daily', label: 'Daily' },
    { value: 'weekly', label: 'Weekly (Monday)' },
];

const SettingsPage = () => {
  const { enqueueSnackbar } = useSnackbar();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
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

      <LoaderOverlay loading={loading}>
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
                  <Typography variant="h6">Notification Settings</Typography>
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
                      placeholder="+1234567890"
                      sx={{ mt: 1 }}
                      size="small"
                    />
                  )}
                </Box>

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
                  <ScheduleIcon sx={{ mr: 1, color: 'text.secondary' }} />
                  <Typography variant="h6">Discovery Settings</Typography>
                </Box>

                <FormControl fullWidth sx={{ mb: 3 }}>
                  <InputLabel>Search Schedule</InputLabel>
                  <Select
                    value={settings.schedule}
                    onChange={handleChange('schedule')}
                    label="Search Schedule"
                  >
                    {SCHEDULE_OPTIONS.map(option => (
                      <MenuItem key={option.value} value={option.value}>
                        {option.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                <Box>
                  <Typography variant="subtitle2" gutterBottom>
                    Minimum Relevance Score
                  </Typography>
                  <TextField
                    type="number"
                    fullWidth
                    value={settings.minRelevanceScore}
                    onChange={handleChange('minRelevanceScore')}
                    InputProps={{
                      endAdornment: '%',
                      inputProps: {
                        min: 0,
                        max: 100,
                      },
                    }}
                    size="small"
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
          <Button
            variant="contained"
            onClick={handleSave}
            disabled={saving || !hasChanges}
            startIcon={<SaveIcon />}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </Box>
      </LoaderOverlay>
    </Box>
  );
};

export default SettingsPage;