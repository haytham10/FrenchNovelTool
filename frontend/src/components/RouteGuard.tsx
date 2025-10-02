"use client";

import React from 'react';
import { useAuth } from './AuthContext';
import { Box, CircularProgress, Paper, Typography } from '@mui/material';
import GoogleLoginButton from './GoogleLoginButton';

export default function RouteGuard({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  
  if (isLoading) {
    return (
      <Box sx={{ display: 'grid', placeItems: 'center', minHeight: '60vh' }}>
        <CircularProgress />
      </Box>
    );
  }
  
  if (user) return <>{children}</>;
  
  return (
    <Box sx={{ display: 'grid', placeItems: 'center', minHeight: '60vh' }}>
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h6" sx={{ mb: 2 }}>Sign in to continue</Typography>
        <GoogleLoginButton />
      </Paper>
    </Box>
  );
}


