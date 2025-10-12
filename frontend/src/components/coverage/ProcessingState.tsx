'use client';

import React from 'react';
import {
  Box,
  Typography,
  Paper,
  LinearProgress,
  Button,
} from '@mui/material';
import { Cancel as CancelIcon } from '@mui/icons-material';

interface ProcessingStateProps {
  progressPercent: number;
}

export default function ProcessingState({ progressPercent }: ProcessingStateProps) {
  const getPhaseInfo = (progress: number) => {
    if (progress < 10) {
      return {
        title: '🔍 Building candidate pool...',
        description: 'Scanning sentences and preparing analysis...',
      };
    }
    if (progress < 50) {
      return {
        title: `📊 Standard mode: ${progress}% coverage...`,
        description: 'Selecting high-value sentences with maximum new words',
      };
    }
    if (progress < 70) {
      return {
        title: `⚡ Ramping up: ${progress}% coverage...`,
        description: 'Increasing coverage with diverse sentence patterns',
      };
    }
    if (progress < 95) {
      return {
        title: `🚀 Aggressive mode: ${progress}% coverage...`,
        description: 'Filling coverage gaps with targeted selections',
      };
    }
    return {
      title: '✨ Finalizing results...',
      description: 'Optimizing final learning set and generating results',
    };
  };

  const phaseInfo = getPhaseInfo(progressPercent);

  return (
    <>
      <Typography variant="h5" fontWeight={600} gutterBottom>
        Processing...
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
        Your vocabulary coverage analysis is in progress
      </Typography>

      <Box sx={{ maxWidth: 600, mx: 'auto', width: '100%' }}>
        {/* Progress Phase Indicator */}
        <Paper elevation={0} variant="outlined" sx={{ p: 3, mb: 4, bgcolor: 'primary.50', borderColor: 'primary.main' }}>
          <Typography variant="body2" color="text.secondary" fontWeight={600} gutterBottom>
            Current Phase
          </Typography>
          <Typography variant="h6" fontWeight={700} color="primary.main">
            {phaseInfo.title}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            {phaseInfo.description}
          </Typography>
        </Paper>

        {/* Progress Bar */}
        <Box sx={{ mb: 4 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body1" fontWeight={600}>Overall Progress</Typography>
            <Typography variant="h6" fontWeight={700} color="primary.main">{progressPercent}%</Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={progressPercent}
            sx={{
              height: 12,
              borderRadius: 2,
              bgcolor: 'action.hover',
              '& .MuiLinearProgress-bar': {
                borderRadius: 2,
                background: 'linear-gradient(90deg, #2196F3 0%, #21CBF3 100%)',
              }
            }}
          />
        </Box>

        <Box sx={{ mt: 4 }}>
          <Button
            variant="outlined"
            color="error"
            startIcon={<CancelIcon />}
            fullWidth
            disabled
          >
            Cancel
          </Button>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1, textAlign: 'center' }}>
            Cancellation coming soon
          </Typography>
        </Box>
      </Box>
    </>
  );
}
