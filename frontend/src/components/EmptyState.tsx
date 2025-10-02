import React from 'react';
import { Box, Typography, Button } from '@mui/material';
import Icon from './Icon';
import { UploadCloud } from 'lucide-react';

export default function EmptyState({ onAction }: { onAction?: () => void }) {
  return (
    <Box sx={{ textAlign: 'center', py: 6 }}>
      <Box sx={{ display: 'inline-flex', p: 2, borderRadius: 3, bgcolor: 'action.hover', mb: 2 }}>
        <Icon icon={UploadCloud} color="primary" fontSize="large" />
      </Box>
      <Typography variant="h6" sx={{ mb: 1 }}>Get started by uploading a PDF</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Drag and drop your file, or click to browse.
      </Typography>
      {onAction && (
        <Button variant="contained" onClick={onAction}>Upload PDF</Button>
      )}
    </Box>
  );
}


