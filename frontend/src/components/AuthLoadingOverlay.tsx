"use client";

import React from 'react';
import { Box, CircularProgress, Typography, Backdrop } from '@mui/material';
import { fadeIn } from '@/lib/animations';

interface AuthLoadingOverlayProps {
  open: boolean;
  message?: string;
}

export default function AuthLoadingOverlay({ open, message }: AuthLoadingOverlayProps) {
  return (
    <Backdrop
      open={open}
      sx={{
        color: '#fff',
        zIndex: (theme) => theme.zIndex.drawer + 2000,
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        backdropFilter: 'blur(8px)',
      }}
    >
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 3,
          animation: `${fadeIn} 0.3s ease-out`,
        }}
      >
        <CircularProgress
          size={64}
          thickness={4}
          sx={{
            color: 'primary.main',
          }}
        />
        <Typography
          variant="h6"
          sx={{
            fontWeight: 500,
            color: 'white',
            textAlign: 'center',
          }}
        >
          {message || 'Signing you in...'}
        </Typography>
        <Typography
          variant="body2"
          sx={{
            color: 'rgba(255, 255, 255, 0.7)',
            textAlign: 'center',
            maxWidth: 400,
          }}
        >
          {message?.includes('Verifying') 
            ? 'Please wait while we verify your authentication token'
            : 'Please wait while we securely authenticate your account'
          }
        </Typography>
      </Box>
    </Backdrop>
  );
}
