import { Alert, Box, Button, CircularProgress, FormControlLabel, Snackbar, Switch, TextField, Typography } from '@mui/material';
import React, { useEffect, useState } from 'react';
import API from '../api/apiClient';

const SettingsPage = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState({ alerts: { sms: false, telegram: false }, schedule: 'Mon/Thu' });
  const [snackbar, setSnackbar] = useState(false);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const data = await API.getUserSettings();
        setSettings(data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchSettings();
  }, []);

  const handleToggle = (key) => (e) => {
    setSettings((prev) => ({ ...prev, alerts: { ...prev.alerts, [key]: e.target.checked } }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await API.updateUserSettings(settings);
      setSnackbar(true);
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <CircularProgress />;

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 3 }}>Settings</Typography>
      <FormControlLabel control={<Switch checked={settings.alerts.telegram} onChange={handleToggle('telegram')} />} label="Telegram Alerts" />
      <TextField label="Phone Number" fullWidth sx={{my:2}} value={settings.alerts.phone||''} onChange={e=>setSettings(prev=>({...prev,alerts:{...prev.alerts,phone:e.target.value}}))} />
      <Box sx={{ mt: 2 }}>
        <Button variant="contained" onClick={handleSave} disabled={saving}>{saving ? 'Saving...' : 'Save'}</Button>
      </Box>
      <Snackbar open={snackbar} autoHideDuration={3000} onClose={()=>setSnackbar(false)}>
        <Alert onClose={()=>setSnackbar(false)} severity="success" sx={{ width: '100%' }}>
          Settings saved!
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default SettingsPage; 