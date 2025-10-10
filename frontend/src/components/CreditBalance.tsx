"use client";

import React from 'react';
import { Box, Chip, Tooltip, CircularProgress, Typography } from '@mui/material';
import { Coins } from 'lucide-react';
import Icon from './Icon';
import { useCredits } from '@/lib/queries';
import { formatDate } from '@/lib/date-utils';

export default function CreditBalance() {
  const { data: credits, isLoading } = useCredits();

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, px: 1 }}>
        <CircularProgress size={16} />
      </Box>
    );
  }

  if (!credits) {
    return null;
  }

  const nextResetDate = credits.next_reset ? new Date(credits.next_reset) : null;
  const formattedDate = nextResetDate ? formatDate(nextResetDate) : '';

  const getBalanceColor = () => {
    if (credits.balance <= 0) return 'error';
    if (credits.balance < 1000) return 'warning';
    return 'success';
  };

  return (
    <Tooltip
      title={
        <Box sx={{ p: 0.5 }}>
          <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
            Credit Balance
          </Typography>
          <Typography variant="caption" display="block">
            Balance: {credits.balance.toLocaleString()} credits
          </Typography>
          <Typography variant="caption" display="block">
            Used: {credits.used.toLocaleString()} credits
          </Typography>
          <Typography variant="caption" display="block">
            Granted: {credits.granted.toLocaleString()} credits
          </Typography>
          {credits.refunded > 0 && (
            <Typography variant="caption" display="block">
              Refunded: {credits.refunded.toLocaleString()} credits
            </Typography>
          )}
          {nextResetDate && (
            <Typography variant="caption" display="block" sx={{ mt: 0.5, opacity: 0.8 }}>
              Resets: {formattedDate}
            </Typography>
          )}
        </Box>
      }
      arrow
    >
      <Chip
        icon={<Icon icon={Coins} fontSize="small" />}
        label={credits.balance.toLocaleString()}
        color={getBalanceColor()}
        variant="outlined"
        size="small"
        sx={{ fontWeight: 600, cursor: 'pointer' }}
      />
    </Tooltip>
  );
}
