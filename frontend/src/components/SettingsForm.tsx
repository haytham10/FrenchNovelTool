'use client';

import React, { useState } from 'react';
import { Box, TextField, Typography, CircularProgress, Paper, Divider, Alert, AlertTitle, Select, MenuItem, FormControl, InputLabel, Button as MuiButton, Stack, Chip } from '@mui/material';
import { Button } from './ui';
import { useSettings, useUpdateSettings } from '@/lib/queries';
import { useAuth } from './AuthContext';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listWordLists, createWordListFromFile } from '@/lib/api';
import Icon from './Icon';
import { User, Save, RefreshCw, CheckCircle, XCircle, Upload, BookOpen } from 'lucide-react';
import type { UserSettings } from '@/lib/api';
import Link from 'next/link';

export default function SettingsForm() {
  // Use React Query for data fetching with optimistic updates
  const { data: settings, isLoading: loading, error } = useSettings();
  const { user } = useAuth();
  const updateSettings = useUpdateSettings();
  const queryClient = useQueryClient();
  
  const [localSettings, setLocalSettings] = useState<Partial<UserSettings>>({});
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  
  // Load word lists
  const { data: wordListsData } = useQuery({
    queryKey: ['wordlists'],
    queryFn: listWordLists,
  });
  
  // Upload word list mutation
  const uploadMutation = useMutation({
    mutationFn: async (data: { file: File; name: string }) => {
      return createWordListFromFile(data.file, data.name, true);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['wordlists'] });
      setLocalSettings(prev => ({
        ...prev,
        default_wordlist_id: data.wordlist.id,
      }));
      setUploadedFile(null);
    },
  });

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

  const handleReconnectGoogle = () => {
    // Trigger Google re-authentication
    window.location.href = '/api/auth/google';
  };
  
  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setUploadedFile(file);
    }
  };
  
  const handleUploadWordList = () => {
    if (uploadedFile) {
      uploadMutation.mutate({
        file: uploadedFile,
        name: uploadedFile.name.replace('.csv', ''),
      });
    }
  };
  
  const wordlists = wordListsData?.wordlists || [];

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
    <Box>
      {/* Google Account Status */}
      <Paper 
        variant="outlined" 
        sx={{ 
          p: 3, 
          mb: 3, 
          bgcolor: user ? 'success.50' : 'warning.50',
          borderColor: user ? 'success.main' : 'warning.main',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
          <Icon icon={user ? CheckCircle : XCircle} color={user ? 'success' : 'warning'} sx={{ fontSize: 32 }} />
          <Box sx={{ flex: 1 }}>
            <Typography variant="h6" fontWeight={600}>
              Google Account Status
            </Typography>
            {user ? (
              <Typography variant="body2" color="text.secondary">
                Connected as {user.email}
              </Typography>
            ) : (
              <Typography variant="body2" color="text.secondary">
                Not connected
              </Typography>
            )}
          </Box>
          <Button
            variant="secondary"
            onClick={handleReconnectGoogle}
            startIcon={<Icon icon={RefreshCw} />}
          >
            {user ? 'Reconnect' : 'Connect'}
          </Button>
        </Box>
        <Alert severity={user ? 'success' : 'warning'} variant="outlined">
          <AlertTitle>
            {user ? 'Google Drive Access Active' : 'Google Drive Access Required'}
          </AlertTitle>
          {user ? (
            'Your account has access to export data to Google Sheets. Click "Reconnect" if you experience any issues.'
          ) : (
            'Connect your Google account to enable exporting processed sentences to Google Sheets.'
          )}
        </Alert>
      </Paper>

      {/* Settings Layout */}
      <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 3 }}>
        {/* Left Column - Processing Settings */}
        <Paper variant="outlined" sx={{ p: 3, flex: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
              <Icon icon={User} color="primary" />
              <Typography variant="h6" fontWeight={600}>
                Processing Settings
              </Typography>
            </Box>
            
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <Box>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Default Sentence Length
                </Typography>
                <TextField
                  label="Target sentence length (words)"
                  type="number"
                  name="sentence_length_limit"
                  value={localSettings.sentence_length_limit ?? settings?.sentence_length_limit ?? ''}
                  onChange={handleSettingChange}
                  inputProps={{ min: 5, max: 20 }}
                  fullWidth
                  size="small"
                  helperText="Default target length for sentence normalization (5-20 words)"
                />
              </Box>

              <Divider />

              <Box>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Default Export Settings
                </Typography>
                <TextField
                  label="Default folder ID (optional)"
                  name="default_folder_id"
                  value={localSettings.default_folder_id ?? settings?.default_folder_id ?? ''}
                  onChange={(e) => setLocalSettings(prev => ({ ...prev, default_folder_id: e.target.value }))}
                  fullWidth
                  size="small"
                  helperText="Google Drive folder ID for default exports"
                  sx={{ mb: 2 }}
                />
                <TextField
                  label="Default sheet name pattern"
                  name="default_sheet_name_pattern"
                  value={localSettings.default_sheet_name_pattern ?? settings?.default_sheet_name_pattern ?? ''}
                  onChange={(e) => setLocalSettings(prev => ({ ...prev, default_sheet_name_pattern: e.target.value }))}
                  fullWidth
                  size="small"
                  helperText="Pattern for naming exported sheets (e.g., 'Novel_{date}')"
                />
              </Box>
            </Box>
          </Paper>

        {/* Right Column - Help & Tips */}
        <Paper variant="outlined" sx={{ p: 3, flex: 1, bgcolor: 'action.hover' }}>
            <Typography variant="h6" fontWeight={600} gutterBottom>
              Settings Guide
            </Typography>
            
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
              <Box>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Sentence Length
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  The target length for normalized sentences. Shorter lengths (5-10) are better for beginner learners, while longer lengths (12-20) preserve more context.
                </Typography>
              </Box>

              <Divider />

              <Box>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Default Folder ID
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  You can find the folder ID in your Google Drive URL. For example, in https://drive.google.com/drive/folders/ABC123, the ID is &quot;ABC123&quot;.
                </Typography>
              </Box>

              <Divider />

              <Box>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Sheet Name Pattern
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Use placeholders like {'{date}'}, {'{time}'}, or {'{filename}'} to automatically generate sheet names. Leave empty to be prompted each time.
                </Typography>
              </Box>
            </Box>
          </Paper>
      </Box>

      {/* Vocabulary Coverage Settings */}
      <Paper variant="outlined" sx={{ p: 3, mt: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
          <Icon icon={BookOpen} color="primary" />
          <Typography variant="h6" fontWeight={600}>
            Vocabulary Coverage Settings
          </Typography>
        </Box>
        
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          <Box>
            <Typography variant="subtitle2" fontWeight={600} gutterBottom>
              Default Word List
            </Typography>
            <FormControl fullWidth size="small">
              <InputLabel>Word List</InputLabel>
              <Select
                value={localSettings.default_wordlist_id ?? settings?.default_wordlist_id ?? ''}
                label="Word List"
                onChange={(e) => setLocalSettings(prev => ({ ...prev, default_wordlist_id: e.target.value as number }))}
              >
                <MenuItem value="">
                  <em>Use global default</em>
                </MenuItem>
                {wordlists.map((wl) => (
                  <MenuItem key={wl.id} value={wl.id}>
                    {wl.name} ({wl.normalized_count} words)
                    {wl.is_global_default && <Chip label="Global Default" size="small" sx={{ ml: 1 }} />}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
              Select the default word list for vocabulary coverage analysis. You can manage word lists on the{' '}
              <Link href="/coverage" style={{ textDecoration: 'none', color: 'inherit', fontWeight: 600 }}>
                Coverage page
              </Link>.
            </Typography>
          </Box>

          <Divider />

          <Box>
            <Typography variant="subtitle2" fontWeight={600} gutterBottom>
              Upload New Word List
            </Typography>
            <Stack direction="row" spacing={2} alignItems="center" sx={{ mt: 1 }}>
              <MuiButton
                component="label"
                variant="outlined"
                startIcon={<Icon icon={Upload} />}
                size="small"
              >
                Choose CSV File
                <input
                  type="file"
                  accept=".csv"
                  hidden
                  onChange={handleFileUpload}
                />
              </MuiButton>
              {uploadedFile && (
                <>
                  <Typography variant="body2">{uploadedFile.name}</Typography>
                  <MuiButton
                    variant="contained"
                    size="small"
                    onClick={handleUploadWordList}
                    disabled={uploadMutation.isPending}
                  >
                    {uploadMutation.isPending ? 'Uploading...' : 'Upload'}
                  </MuiButton>
                </>
              )}
            </Stack>
            {uploadMutation.isError && (
              <Alert severity="error" sx={{ mt: 1 }}>
                Failed to upload word list
              </Alert>
            )}
            {uploadMutation.isSuccess && (
              <Alert severity="success" sx={{ mt: 1 }}>
                Word list uploaded successfully and set as default!
              </Alert>
            )}
          </Box>
        </Box>
      </Paper>

      {/* Save Button */}
      <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
        <Button
          variant="ghost"
          onClick={() => setLocalSettings({})}
          disabled={Object.keys(localSettings).length === 0}
        >
          Reset Changes
        </Button>
        <Button 
          variant="primary"
          onClick={handleSaveSettings}
          loading={updateSettings.isPending}
          disabled={Object.keys(localSettings).length === 0}
          startIcon={<Icon icon={Save} />}
        >
          Save Settings
        </Button>
      </Box>
    </Box>
  );
}
