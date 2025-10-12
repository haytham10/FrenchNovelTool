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
} from '@mui/material';

interface ExportDialogProps {
  open: boolean;
  onClose: () => void;
  sheetName: string;
  setSheetName: (name: string) => void;
  onExport: () => void;
  exporting: boolean;
}

export default function ExportDialog({
  open,
  onClose,
  sheetName,
  setSheetName,
  onExport,
  exporting,
}: ExportDialogProps) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Export to Google Sheets</DialogTitle>
      <DialogContent>
        <TextField
          fullWidth
          label="Sheet Name"
          value={sheetName}
          onChange={(e) => setSheetName(e.target.value)}
          sx={{ mt: 2 }}
          placeholder="Coverage Results"
        />
        <Alert severity="info" sx={{ mt: 2 }}>
          This will create a new Google Spreadsheet with your coverage results.
          Make sure you have connected your Google account in Settings.
        </Alert>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          onClick={onExport}
          disabled={!sheetName || exporting}
        >
          {exporting ? 'Exporting...' : 'Export'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
