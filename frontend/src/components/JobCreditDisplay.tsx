"use client";

import React from 'react';
import { Box, Typography, Tooltip, Chip, CircularProgress } from '@mui/material';
import { Coins, TrendingUp, TrendingDown } from 'lucide-react';
import Icon from './Icon';
import { useJob } from '@/lib/queries';

interface JobCreditDisplayProps {
  jobId: number;
}

export default function JobCreditDisplay({ jobId }: JobCreditDisplayProps) {
  const { data: job, isLoading } = useJob(jobId);

  if (isLoading) {
    return <CircularProgress size={16} />;
  }

  if (!job) {
    return (
      <Typography variant="caption" color="text.secondary">
        -
      </Typography>
    );
  }

  const isRefunded = job.status === 'failed' || job.status === 'cancelled';
  // Use nullish coalescing so that null/undefined actual_credits are preserved
  // and don't display as 0 while a job is still processing.
  const actualCredits: number | null = job.actual_credits ?? null;
  const estimatedCredits = job.estimated_credits;
  const difference: number | null = actualCredits !== null ? actualCredits - estimatedCredits : null;

  return (
    <Tooltip
      title={
        <Box sx={{ p: 0.5 }}>
          <Typography variant="caption" display="block" fontWeight={600}>
            Credit Details
          </Typography>
          <Typography variant="caption" display="block">
            Estimated: {estimatedCredits} credits
          </Typography>
          {job.status === 'completed' && actualCredits !== null && (
            <>
              <Typography variant="caption" display="block">
                Actual: {actualCredits} credits
              </Typography>
              {difference !== null && difference !== 0 && (
                <Typography variant="caption" display="block" color={difference > 0 ? 'error.light' : 'success.light'}>
                  Adjustment: {difference > 0 ? '+' : ''}{difference} credits
                </Typography>
              )}
            </>
          )}
          {isRefunded && (
            <Typography variant="caption" display="block" color="success.light">
              Refunded: {estimatedCredits} credits
            </Typography>
          )}
          <Typography variant="caption" display="block" sx={{ mt: 0.5, opacity: 0.8 }}>
            Model: {job.model}
          </Typography>
        </Box>
      }
      arrow
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
        {isRefunded ? (
          <Chip
            icon={<Icon icon={Coins} fontSize="small" />}
            label="Refunded"
            size="small"
            color="success"
            variant="outlined"
            sx={{ fontSize: '0.7rem' }}
          />
        ) : job.status === 'completed' ? (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Typography variant="body2" fontWeight={600}>
              {actualCredits ?? estimatedCredits}
            </Typography>
            {difference !== null && difference !== 0 && (
              <Icon
                icon={difference > 0 ? TrendingUp : TrendingDown}
                fontSize="small"
                sx={{ color: difference > 0 ? 'error.main' : 'success.main' }}
              />
            )}
          </Box>
        ) : (
          <Typography variant="body2" color="text.secondary">
            {estimatedCredits} (est.)
          </Typography>
        )}
      </Box>
    </Tooltip>
  );
}
