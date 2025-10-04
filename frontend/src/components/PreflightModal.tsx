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
  Divider,
  Stack,
  Chip,
} from '@mui/material';
import { AlertCircle, CheckCircle, Coins, Zap } from 'lucide-react';
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

  const getModelLabel = (preference: string) => {
    const labels: Record<string, string> = {
      balanced: 'Balanced',
      speed: 'Speed',
    };
    return labels[preference] || preference;
  };

  const getModelDescription = (preference: string) => {
    const descriptions: Record<string, string> = {
      balanced: 'Best balance of speed and quality',
      speed: 'Fastest processing, good quality',
    };
    return descriptions[preference] || '';
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 2,
        },
      }}
    >
      <DialogTitle sx={{ pb: 1 }}>
        <Typography variant="h6" component="div" sx={{ fontWeight: 700 }}>
          Confirm Processing
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          {fileName}
        </Typography>
      </DialogTitle>

      <DialogContent>
        {loading ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 4 }}>
            <CircularProgress size={40} sx={{ mb: 2 }} />
            <Typography variant="body2" color="text.secondary">
              Estimating cost...
            </Typography>
          </Box>
        ) : estimate ? (
          <Stack spacing={2}>
            {!estimate.allowed && (
              <Alert severity="error" icon={<Icon icon={AlertCircle} />}>
                <Typography variant="body2" fontWeight={600}>
                  Insufficient Credits
                </Typography>
                <Typography variant="caption">
                  {estimate.message || 'You do not have enough credits to process this file.'}
                </Typography>
              </Alert>
            )}

            <Box>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Processing Model
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Chip
                  icon={<Icon icon={Zap} fontSize="small" />}
                  label={getModelLabel(estimate.model_preference)}
                  color="primary"
                  size="small"
                />
                <Typography variant="caption" color="text.secondary">
                  {getModelDescription(estimate.model_preference)}
                </Typography>
                {estimate.model_preference === 'quality' && (
                  <Typography variant="caption" sx={{ color: 'warning.main', fontWeight: 600, display: 'block', mt: 0.5 }}>
                    Quality model detected — MY WALLET IS ALREADY DRY :( (uses gemini-2.5-pro, expensive)
                  </Typography>
                )}
              </Box>
            </Box>

            <Divider />

            <Box>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Cost Breakdown
              </Typography>
              <Stack spacing={1}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="body2">Estimated Tokens:</Typography>
                  <Typography variant="body2" fontWeight={600}>
                    {estimate.estimated_tokens.toLocaleString()}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="body2">Pricing Rate:</Typography>
                  <Typography variant="body2" fontWeight={600}>
                    {estimate.pricing_rate} credits / 1K tokens
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="body2">Estimation Method:</Typography>
                  <Chip
                    label={estimate.estimation_method === 'api' ? 'API' : 'Heuristic'}
                    size="small"
                    variant="outlined"
                    sx={{ height: 20, fontSize: '0.7rem' }}
                  />
                </Box>
              </Stack>
            </Box>

            <Divider />

            <Box>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Credit Summary
              </Typography>
              <Stack spacing={1}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="body2">Current Balance:</Typography>
                  <Typography variant="body2" fontWeight={600}>
                    {estimate.current_balance.toLocaleString()} credits
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="body2" color="error.main">
                    Estimated Cost:
                  </Typography>
                  <Typography variant="body2" fontWeight={700} color="error.main">
                    -{estimate.estimated_credits.toLocaleString()} credits
                  </Typography>
                </Box>
                <Divider sx={{ my: 0.5 }} />
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="body2" fontWeight={600}>
                    Remaining Balance:
                  </Typography>
                  <Typography
                    variant="body2"
                    fontWeight={700}
                    color={
                      estimate.current_balance - estimate.estimated_credits >= 0
                        ? 'success.main'
                        : 'error.main'
                    }
                  >
                    {(estimate.current_balance - estimate.estimated_credits).toLocaleString()} credits
                  </Typography>
                </Box>
              </Stack>
            </Box>

            {estimate.allowed && (
              <Alert severity="info" icon={<Icon icon={CheckCircle} />}>
                <Typography variant="caption">
                  Credits will be reserved now and adjusted based on actual usage after processing completes.
                  Full refund if processing fails.
                </Typography>
              </Alert>
            )}
          </Stack>
        ) : (
          <Alert severity="error">
            Failed to estimate cost. Please try again.
          </Alert>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} disabled={confirming}>
          Cancel
        </Button>
        <Button
          onClick={handleConfirm}
          variant="contained"
          disabled={!estimate || !estimate.allowed || loading || confirming}
          startIcon={confirming ? <CircularProgress size={16} /> : <Icon icon={Coins} fontSize="small" />}
        >
          {confirming ? 'Confirming...' : 'Confirm & Process'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
