"use client";

import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  CircularProgress,
  Alert,
} from '@mui/material';
import { Coins } from 'lucide-react';
import Icon from './Icon';
import type { CostEstimate } from '@/lib/types';

interface PreflightModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  estimate: CostEstimate | null;
  loading: boolean;
  fileName: string;
}

export default function PreflightModal({
  open,
  onClose,
  onConfirm,
  estimate,
  loading,
  fileName,
}: PreflightModalProps) {
  const [confirming, setConfirming] = useState(false);

  const handleConfirm = async () => {
    setConfirming(true);
    try {
      await onConfirm();
    } finally {
      setConfirming(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="xs"
      fullWidth
      slotProps={{
        paper: {
          sx: {
            borderRadius: 2,
          },
        },
      }}
    >
      <DialogTitle sx={{ pb: 1 }}>
        Ready to Process
      </DialogTitle>

      <DialogContent>
        {loading ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 3 }}>
            <CircularProgress size={40} sx={{ mb: 2 }} />
            <Typography variant="body2" color="text.secondary">
              Estimating cost...
            </Typography>
          </Box>
        ) : (
          <Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {fileName}
            </Typography>

            {estimate && !estimate.allowed && (
              <Alert severity="error" sx={{ mb: 2 }}>
                <Typography variant="body2">
                  {estimate.message || 'Insufficient credits'}
                </Typography>
              </Alert>
            )}

            {estimate && (
              <Box sx={{ 
                p: 2, 
                bgcolor: 'action.hover', 
                borderRadius: 2,
                border: 1,
                borderColor: 'divider'
              }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="body2" color="text.secondary">
                    Estimated Cost
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <Icon icon={Coins} sx={{ fontSize: 18, color: 'primary.main' }} />
                    <Typography variant="h6" fontWeight={700} color="primary">
                      {estimate.estimated_credits}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      credits
                    </Typography>
                  </Box>
                </Box>
                <Box sx={{ mt: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="caption" color="text.secondary">
                    Your Balance
                  </Typography>
                  <Typography variant="caption" fontWeight={600}>
                    {estimate.current_balance.toLocaleString()} credits
                  </Typography>
                </Box>
              </Box>
            )}
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ p: 2, pt: 0 }}>
        <Button onClick={onClose} disabled={confirming}>
          Cancel
        </Button>
        <Button
          onClick={handleConfirm}
          variant="contained"
          disabled={!!(loading || confirming || (estimate && !estimate.allowed))}
          startIcon={confirming ? <CircularProgress size={16} /> : estimate && <Icon icon={Coins} sx={{ fontSize: 18 }} />}
          sx={{ minWidth: 140 }}
        >
          {confirming ? 'Processing...' : estimate ? `Process (${estimate.estimated_credits} credits)` : 'Process'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
