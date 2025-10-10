import React, { useEffect, useState } from 'react';
import { Button, Box, Typography } from '@mui/material';
import { useSnackbar } from 'notistack';

interface DriveFolderPickerProps {
  onFolderSelect: (folderId: string, folderName: string) => void;
  selectedFolderName: string | null;
  onClearSelection?: () => void;
  onPickerOpen?: () => void;
  onPickerCancel?: () => void;
}

const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
const API_KEY = process.env.NEXT_PUBLIC_GOOGLE_API_KEY;

// Lightweight custom Google Drive Picker implementation
// Replaces react-google-drive-picker to reduce bundle size
const loadGooglePicker = async (): Promise<typeof google> => {
  // Check if already loaded
  if (typeof window !== 'undefined' && window.google) {
    return window.google;
  }

  // Load Google API script
  await new Promise<void>((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://apis.google.com/js/api.js';
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Failed to load Google API'));
    document.head.appendChild(script);
  });

  // Wait for gapi to be ready
  await new Promise<void>((resolve) => {
    window.gapi.load('picker', () => resolve());
  });

  return window.google;
};

export default function DriveFolderPicker({ 
  onFolderSelect, 
  selectedFolderName, 
  onClearSelection,
  onPickerOpen,
  onPickerCancel
}: DriveFolderPickerProps) {
  const [missingCredentials, setMissingCredentials] = useState(false);
  const [loading, setLoading] = useState(false);
  const { enqueueSnackbar } = useSnackbar();

  useEffect(() => {
    if (!CLIENT_ID || !API_KEY) {
      setMissingCredentials(true);
      enqueueSnackbar('Google API credentials are not configured. Folder selection is disabled.', { 
        variant: 'warning' 
      });
    }
  }, [enqueueSnackbar]);

  const handleOpenPicker = async () => {
    if (missingCredentials) {
      enqueueSnackbar('Google API credentials are required before selecting a folder.', { 
        variant: 'error' 
      });
      return;
    }

    if (!CLIENT_ID || !API_KEY) {
      enqueueSnackbar('Google API credentials are missing.', { variant: 'error' });
      return;
    }

    try {
      setLoading(true);
      onPickerOpen?.();

      // Load Google Picker API
      const google = await loadGooglePicker();

      // Get OAuth token from localStorage (set by AuthContext)
      const accessToken = localStorage.getItem('accessToken');
      if (!accessToken) {
        enqueueSnackbar('Please sign in to select a folder.', { variant: 'error' });
        setLoading(false);
        return;
      }

      // Create and show picker
      const view = new google.picker.DocsView(google.picker.ViewId.FOLDERS)
        .setSelectFolderEnabled(true)
        .setIncludeFolders(true);

      const picker = new google.picker.PickerBuilder()
        .addView(view)
        .setOAuthToken(accessToken)
        .setDeveloperKey(API_KEY)
        .setCallback((data: google.picker.ResponseObject) => {
          if (data.action === google.picker.Action.CANCEL) {
            onPickerCancel?.();
          } else if (data.action === google.picker.Action.PICKED && data.docs && data.docs.length > 0) {
            const folder = data.docs[0];
            onFolderSelect(folder.id, folder.name);
            enqueueSnackbar(`Folder "${folder.name}" selected`, { variant: 'success' });
          }
          setLoading(false);
        })
        .build();

      picker.setVisible(true);
    } catch (error) {
      console.error('Error opening picker:', error);
      enqueueSnackbar('Failed to open folder picker.', { variant: 'error' });
      setLoading(false);
    }
  };

  return (
    <Box mt={2}>
      <Typography variant="subtitle1" gutterBottom>
        Google Drive Destination (Optional)
      </Typography>
      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
        <Button 
          variant="outlined" 
          onClick={handleOpenPicker} 
          disabled={missingCredentials || loading}
        >
          {loading ? 'Loading...' : 'Select Folder'}
        </Button>
        {selectedFolderName && onClearSelection && (
          <Button variant="text" size="small" onClick={onClearSelection}>
            Clear
          </Button>
        )}
      </Box>
      {selectedFolderName && (
        <Typography variant="body2" color="textSecondary" mt={1}>
          Selected: {selectedFolderName}
        </Typography>
      )}
    </Box>
  );
}
