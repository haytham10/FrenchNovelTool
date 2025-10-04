import React, { useCallback, useEffect, useState } from 'react';
import { Button, Box, Typography } from '@mui/material';
import { useSnackbar } from 'notistack';

interface DriveFolderPickerProps {
  onFolderSelect: (folderId: string, folderName: string) => void;
  selectedFolderName: string | null;
  onClearSelection?: () => void;
}

declare global {
  interface Window {
    gapi?: {
      load: (library: string, callback: () => void) => void;
      client: {
        init: (options: { apiKey: string; discoveryDocs: string[] }) => Promise<void>;
      };
      picker: {
        View: new (viewId: string) => { setMimeTypes: (types: string) => void };
        ViewId: { FOLDERS: string };
        Action: { PICKED: string };
        PickerBuilder: new () => PickerBuilder;
      };
    };
    google?: {
      accounts: {
        oauth2: {
          initTokenClient: (options: {
            client_id: string;
            scope: string;
            callback: (response: { access_token?: string; error?: string }) => void;
          }) => TokenClient;
        };
      };
      gapi: NonNullable<Window['gapi']>;
    };
  }
}

type TokenClient = {
  requestAccessToken: () => void;
};

type PickerCallbackData = {
  action: string;
  docs: Array<{ id: string; name: string }>;
};

interface PickerBuilder {
  addView: (view: unknown) => PickerBuilder;
  setOAuthToken: (token: string) => PickerBuilder;
  setDeveloperKey: (key: string) => PickerBuilder;
  setCallback: (callback: (data: PickerCallbackData) => void) => PickerBuilder;
  build: () => { setVisible: (visible: boolean) => void };
}

// Note: Discovery docs are loaded automatically by the Picker API, no need to pre-fetch
const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
const API_KEY = process.env.NEXT_PUBLIC_GOOGLE_API_KEY;
const SCOPES = 'https://www.googleapis.com/auth/drive.file';

export default function DriveFolderPicker({ onFolderSelect, selectedFolderName, onClearSelection }: DriveFolderPickerProps) {
  const [gapiLoaded, setGapiLoaded] = useState(false);
  const [gisLoaded, setGisLoaded] = useState(false);
  const [tokenClient, setTokenClient] = useState<TokenClient | null>(null);
  const [missingCredentials, setMissingCredentials] = useState(false);
  const { enqueueSnackbar } = useSnackbar();

  const createPicker = useCallback((accessToken: string) => {
    if (!gapiLoaded) {
      enqueueSnackbar('Google API client not loaded.', { variant: 'error' });
      return;
    }

    const googleInstance = window.google;
    const gapiInstance = googleInstance?.gapi;
    const pickerApi = gapiInstance?.picker;

    if (!googleInstance || !gapiInstance || !pickerApi) {
      enqueueSnackbar('Google Picker API is unavailable.', { variant: 'error' });
      return;
    }

    const view = new pickerApi.View(pickerApi.ViewId.FOLDERS);
    view.setMimeTypes('application/vnd.google-apps.folder');

    const picker = new pickerApi.PickerBuilder()
      .addView(view)
      .setOAuthToken(accessToken)
      .setDeveloperKey(API_KEY ?? '')
      .setCallback((data: PickerCallbackData) => {
        if (data.action === pickerApi.Action.PICKED) {
          const doc = data.docs[0];
          onFolderSelect(doc.id, doc.name);
        }
      })
      .build();
    picker.setVisible(true);
  }, [enqueueSnackbar, gapiLoaded, onFolderSelect]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    if (!CLIENT_ID || !API_KEY) {
      setMissingCredentials(true);
      enqueueSnackbar('Google API credentials are not configured. Folder selection is disabled.', { variant: 'warning' });
      return;
    }

    const loadGapi = () => {
      const gapiInstance = window.gapi;
      if (!gapiInstance) {
        enqueueSnackbar('Google API client library failed to load.', { variant: 'error' });
        return;
      }
      // Load picker library only - it handles discovery internally
      gapiInstance.load('picker', () => {
        setGapiLoaded(true);
      });
    };

    const loadGis = () => {
      const googleInstance = window.google;
      const oauth2 = googleInstance?.accounts?.oauth2;

      if (!googleInstance || !oauth2) {
        enqueueSnackbar('Google Identity Services library failed to load.', { variant: 'error' });
        return;
      }

      const tokenClientInstance = oauth2.initTokenClient({
        client_id: CLIENT_ID,
        scope: SCOPES,
        callback: (resp: { access_token?: string; error?: string }) => {
          if (resp.error) {
            enqueueSnackbar(`Authentication error: ${resp.error}`, { variant: 'error' });
            return;
          }
          if (!resp.access_token) {
            enqueueSnackbar('Access token missing from Google response.', { variant: 'error' });
            return;
          }
          createPicker(resp.access_token);
        },
      });

      if (!tokenClientInstance) {
        enqueueSnackbar('Failed to initialise Google Identity Services client.', { variant: 'error' });
        return;
      }

      setTokenClient(tokenClientInstance);
      setGisLoaded(true);
    };

    // Load GAPI and GIS scripts if not already loaded
    if (!window.gapi) {
      const script = document.createElement('script');
      script.src = "https://apis.google.com/js/api.js";
      script.onload = loadGapi;
      document.head.appendChild(script);
    } else {
      loadGapi();
    }

    if (!window.google) {
      const script = document.createElement('script');
      script.src = "https://accounts.google.com/gsi/client";
      script.onload = loadGis;
      document.head.appendChild(script);
    } else {
      loadGis();
    }
  }, [createPicker, enqueueSnackbar]);

  const handlePickFolder = () => {
    if (missingCredentials) {
      enqueueSnackbar('Google API credentials are required before selecting a folder.', { variant: 'error' });
      return;
    }
    if (!gisLoaded) {
      enqueueSnackbar('Google Identity Services not loaded.', { variant: 'error' });
      return;
    }
    if (!tokenClient) {
      enqueueSnackbar('Token client is not ready yet.', { variant: 'error' });
      return;
    }
    tokenClient.requestAccessToken();
  };

  return (
    <Box mt={2}>
      <Typography variant="subtitle1" gutterBottom>Google Drive Destination (Optional)</Typography>
      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
        <Button variant="outlined" onClick={handlePickFolder} disabled={!gapiLoaded || !gisLoaded}>
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
