'use client';

import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Alert,
  Typography,
} from '@mui/material';

interface ImportDialogProps {
  open: boolean;
  onClose: () => void;
  sheetUrl: string;
  setSheetUrl: (url: string) => void;
  onImport: () => void;
  importing: boolean;
}

export default function ImportDialog({
  open,
  onClose,
  sheetUrl,
  setSheetUrl,
  onImport,
  importing,
}: ImportDialogProps) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Import Sentences from Google Sheets</DialogTitle>
      <DialogContent>
        <TextField
          fullWidth
          label="Google Sheets URL"
          value={sheetUrl}
          onChange={(e) => setSheetUrl(e.target.value)}
          sx={{ mt: 2 }}
          placeholder="https://docs.google.com/spreadsheets/d/..."
          helperText="Paste the full URL or just the spreadsheet ID"
        />
        <Alert severity="info" sx={{ mt: 2 }}>
          <Typography variant="body2" gutterBottom>
            <strong>Sheet Format:</strong>
          </Typography>
          <Typography variant="body2" component="div">
            • Column A: Index (optional, e.g., 1, 2, 3...)
            <br />
            • Column B: Sentence (French sentences)
            <br />
            <br />
            The first row will be detected as a header and skipped if it contains
            &ldquo;Index&rdquo; or &ldquo;Sentence&rdquo;.
          </Typography>
        </Alert>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          onClick={onImport}
          disabled={!sheetUrl || importing}
        >
          {importing ? 'Importing...' : 'Import'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
