'use client';

import React, { useState } from 'react';
import { Box, TextField, Typography, CircularProgress } from '@mui/material';
import { Button } from './ui';
import { useSettings, useUpdateSettings } from '@/lib/queries';
import type { UserSettings } from '@/lib/api';

export default function SettingsForm() {
  // Use React Query for data fetching with optimistic updates
  const { data: settings, isLoading: loading, error } = useSettings();
  const updateSettings = useUpdateSettings();
  
  const [localSettings, setLocalSettings] = useState<Partial<UserSettings>>({});

  const handleSettingChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = event.target;
    setLocalSettings(prev => ({
      ...prev,
      [name]: Number(value),
    }));
  };

  const handleSaveSettings = async () => {
    if (Object.keys(localSettings).length === 0) return;

    // Use mutation with optimistic updates
    await updateSettings.mutateAsync(localSettings);
    setLocalSettings({}); // Clear local changes after save
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
        <Typography variant="body1" color="error">Failed to load settings</Typography>
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
        value={localSettings.sentence_length_limit ?? settings?.sentence_length_limit ?? ''}
        onChange={handleSettingChange}
        inputProps={{ min: 1 }}
        fullWidth
      />
      <Button 
        variant="primary"
        onClick={handleSaveSettings}
        loading={updateSettings.isPending}
        disabled={Object.keys(localSettings).length === 0}
      >
        Save Settings
      </Button>
    </Box>
  );
}
