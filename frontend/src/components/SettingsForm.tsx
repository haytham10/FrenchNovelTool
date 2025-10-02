'use client';

import React, { useEffect, useState } from 'react';
import { Box, TextField, Button, Typography, CircularProgress } from '@mui/material';
import { useSnackbar } from 'notistack';
import { fetchSettings as fetchUserSettings, saveSettings, getApiErrorMessage } from '@/lib/api';
import type { UserSettings } from '@/lib/types';

export default function SettingsForm() {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { enqueueSnackbar } = useSnackbar();

  useEffect(() => {
    const loadSettings = async () => {
      try {
        const data = await fetchUserSettings();
        setSettings(data);
      } catch (error) {
        const errorMessage = getApiErrorMessage(error, 'Failed to fetch settings.');
        enqueueSnackbar(errorMessage, { variant: 'error' });
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
  };
  loadSettings();
  }, [enqueueSnackbar]);

  const handleSettingChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = event.target;
    setSettings(prevSettings => {
      if (!prevSettings) {
        return prevSettings;
      }
      return {
        ...prevSettings,
        [name]: Number(value),
      };
    });
  };

  const handleSaveSettings = async () => {
    if (!settings) return;

    setSaving(true);
    try {
      await saveSettings(settings);
      enqueueSnackbar('Settings saved successfully!', { variant: 'success' });
    } catch (error) {
      enqueueSnackbar(getApiErrorMessage(error, 'Failed to save settings.'), { variant: 'error' });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
        <CircularProgress />
        <Typography variant="body1" color="textSecondary" ml={2}>Loading settings...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
        <Typography variant="body1" color="error">Error: {error}</Typography>
      </Box>
    );
  }

  return (
    <Box component="form" sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Typography variant="h6" gutterBottom>Sentence Processing Settings</Typography>
      <TextField
        label="Sentence Length Limit (words)"
        type="number"
        name="sentence_length_limit"
        value={settings?.sentence_length_limit || ''}
        onChange={handleSettingChange}
        inputProps={{ min: 1 }}
        fullWidth
      />
      <Button 
        variant="contained"
        color="primary"
        onClick={handleSaveSettings}
        disabled={saving}
      >
        {saving ? <CircularProgress size={24} color="inherit" /> : 'Save Settings'}
      </Button>
    </Box>
  );
}
