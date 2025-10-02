'use client';

import React from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, Typography, Box, Chip, Divider } from '@mui/material';
import Icon from './Icon';
import { Sparkles, CheckCircle, Zap, Shield } from 'lucide-react';

interface ChangelogModalProps {
  open: boolean;
  onClose: () => void;
}

export default function ChangelogModal({ open, onClose }: ChangelogModalProps) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Icon icon={Sparkles} color="primary" />
          <Typography variant="h6">What&apos;s New</Typography>
        </Box>
      </DialogTitle>
      <DialogContent>
        {/* Version 2.0 - P1 Release */}
        <Box sx={{ mb: 4 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
            <Chip label="v2.0" color="primary" />
            <Typography variant="caption" color="text.secondary">
              January 2025
            </Typography>
          </Box>
          <Typography variant="h6" sx={{ mb: 2 }}>
            P1: High-Priority UX/UI Improvements
          </Typography>

          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, fontWeight: 600 }}>
              <Icon icon={Zap} fontSize="small" color="primary" />
              Advanced Normalization Controls
            </Typography>
            <Box component="ul" sx={{ pl: 4, color: 'text.secondary' }}>
              <li>Live preview: paste sample text and see split result</li>
              <li>Advanced options: ignore dialogues, preserve quotes, fix hyphenations</li>
              <li>Gemini model selector (balanced/quality/speed)</li>
              <li>Minimum sentence length configuration</li>
            </Box>
          </Box>

          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, fontWeight: 600 }}>
              <Icon icon={CheckCircle} fontSize="small" color="success" />
              Results Table Power Features
            </Typography>
            <Box component="ul" sx={{ pl: 4, color: 'text.secondary' }}>
              <li>Toggle between original vs normalized text per row</li>
              <li>Visual highlights for long sentences with word count meter</li>
              <li>Bulk actions: approve all, export selected only</li>
              <li>Column resizing and keyboard multi-select (Shift+click)</li>
            </Box>
          </Box>

          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, fontWeight: 600 }}>
              <Icon icon={Shield} fontSize="small" color="info" />
              Enhanced Authentication & UX
            </Typography>
            <Box component="ul" sx={{ pl: 4, color: 'text.secondary' }}>
              <li>Dedicated login page with deep linking</li>
              <li>Private routes now require authentication</li>
              <li>Streamlined hero section with prominent Upload button</li>
              <li>Drag-and-drop integrated into Upload button</li>
              <li>Improved accessibility and keyboard navigation</li>
            </Box>
          </Box>

          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, fontWeight: 600 }}>
              <Icon icon={Sparkles} fontSize="small" color="warning" />
              History & Troubleshooting
            </Typography>
            <Box component="ul" sx={{ pl: 4, color: 'text.secondary' }}>
              <li>Enhanced error logs with error codes and failed steps</li>
              <li>Retry and duplicate run actions (UI ready)</li>
              <li>In-app help modal with troubleshooting guides</li>
              <li>Better empty states with illustrations</li>
            </Box>
          </Box>
        </Box>

        <Divider sx={{ my: 3 }} />

        {/* Version 1.0 - P0 Release */}
        <Box sx={{ mb: 4 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
            <Chip label="v1.0" />
            <Typography variant="caption" color="text.secondary">
              December 2024
            </Typography>
          </Box>
          <Typography variant="h6" sx={{ mb: 2 }}>
            P0: Core Functionality
          </Typography>
          <Box component="ul" sx={{ pl: 4, color: 'text.secondary' }}>
            <li>PDF upload and text extraction</li>
            <li>Sentence normalization with Google Gemini</li>
            <li>Direct export to Google Sheets</li>
            <li>Processing history</li>
            <li>User settings and preferences</li>
            <li>Google OAuth integration</li>
          </Box>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} variant="contained">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
}
