import React from 'react';
import { Box, Typography, Button } from '@mui/material';
import Icon from './Icon';
import { UploadCloud, type LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon?: LucideIcon;
  title?: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  illustration?: React.ReactNode;
}

export default function EmptyState({ 
  icon = UploadCloud,
  title = "Get started by uploading a PDF",
  description = "Upload your French novel PDF to begin sentence normalization.",
  actionLabel = "Upload PDF",
  onAction,
  illustration
}: EmptyStateProps) {
  return (
    <Box sx={{ textAlign: 'center', py: 8 }}>
      {illustration || (
        <Box sx={{ 
          display: 'inline-flex', 
          p: 3, 
          borderRadius: 4, 
          bgcolor: 'action.hover',
          border: 2,
          borderColor: 'divider',
          mb: 3 
        }}>
          <Icon icon={icon} color="primary" sx={{ fontSize: 64 }} />
        </Box>
      )}
      <Typography variant="h5" sx={{ mb: 2, fontWeight: 600 }}>
        {title}
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4, maxWidth: 500, mx: 'auto' }}>
        {description}
      </Typography>
      {onAction && (
        <Button variant="contained" size="large" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </Box>
  );
}


