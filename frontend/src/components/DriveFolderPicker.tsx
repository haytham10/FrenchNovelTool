import React, { useEffect, useState } from 'react';
import { Button, Box, Typography } from '@mui/material';
import { useSnackbar } from 'notistack';
import useDrivePicker from 'react-google-drive-picker';

interface DriveFolderPickerProps {
  onFolderSelect: (folderId: string, folderName: string) => void;
  selectedFolderName: string | null;
  onClearSelection?: () => void;
  onPickerOpen?: () => void;
  onPickerCancel?: () => void;
}

const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
const API_KEY = process.env.NEXT_PUBLIC_GOOGLE_API_KEY;

export default function DriveFolderPicker({ 
  onFolderSelect, 
  selectedFolderName, 
  onClearSelection,
  onPickerOpen,
  onPickerCancel
}: DriveFolderPickerProps) {
  const [openPicker] = useDrivePicker();
  const [missingCredentials, setMissingCredentials] = useState(false);
  const { enqueueSnackbar } = useSnackbar();

  useEffect(() => {
    if (!CLIENT_ID || !API_KEY) {
      setMissingCredentials(true);
      enqueueSnackbar('Google API credentials are not configured. Folder selection is disabled.', { 
        variant: 'warning' 
      });
    }
  }, [enqueueSnackbar]);

  const handleOpenPicker = () => {
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

    // Notify parent that picker is opening
    onPickerOpen?.();

    openPicker({
      clientId: CLIENT_ID,
      developerKey: API_KEY,
      viewId: 'FOLDERS',
      setSelectFolderEnabled: true,
      setIncludeFolders: true,
      supportDrives: true,
      multiselect: false,
      // Match backend OAuth scopes exactly to avoid scope mismatch errors
      customScopes: [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile',
        'openid',
        'https://www.googleapis.com/auth/drive.file'
      ],
      callbackFunction: (data) => {
        if (data.action === 'cancel') {
          console.log('[DriveFolderPicker] User cancelled folder selection');
          onPickerCancel?.();
          return;
        }
        
        if (data.action === 'picked' && data.docs && data.docs.length > 0) {
          const folder = data.docs[0];
          console.log('[DriveFolderPicker] Folder selected:', folder);
          onFolderSelect(folder.id, folder.name);
          enqueueSnackbar(`Folder "${folder.name}" selected`, { variant: 'success' });
        }
      },
    });
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
          disabled={missingCredentials}
        >
          Select Folder
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
