'use client';

import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Stack,
  Box,
  Typography,
  Divider,
} from '@mui/material';

interface HelpDialogProps {
  open: boolean;
  onClose: () => void;
}

export default function HelpDialog({ open, onClose }: HelpDialogProps) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>About Analysis Modes</DialogTitle>
      <DialogContent>
        <Stack spacing={3} sx={{ mt: 1 }}>
          <Box>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Coverage Mode
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Finds the minimum number of sentences needed to cover every word in your target list at least once.
              This mode prioritizes comprehensive vocabulary exposure, making it ideal for creating complete learning sets.
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              <strong>Best for:</strong> Ensuring complete vocabulary coverage, comprehensive learning materials
            </Typography>
          </Box>

          <Divider />

          <Box>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Filter Mode
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Selects sentences with high vocabulary density (≥95% common words) that are 4-8 words in length.
              Prioritizes shorter, high-quality sentences perfect for daily repetition drills.
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              <strong>Best for:</strong> Daily practice, drilling exercises, beginner-friendly materials
            </Typography>
          </Box>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} variant="contained">
          Got it
        </Button>
      </DialogActions>
    </Dialog>
  );
}
