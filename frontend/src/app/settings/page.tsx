'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import { Box, Typography, Paper, Button, Container, Skeleton } from '@mui/material';
import Link from 'next/link';
import RouteGuard from '@/components/RouteGuard';
import Breadcrumbs from '@/components/Breadcrumbs';

// Lazy load the SettingsForm
const SettingsForm = dynamic(() => import('@/components/SettingsForm'), {
  loading: () => <Skeleton variant="rectangular" height={400} />,
  ssr: false,
});

export default function SettingsPage() {
  return (
    <Container maxWidth="lg" sx={{ py: 6 }}>
      <Breadcrumbs items={[{ label: 'Home', href: '/' }, { label: 'Settings' }]} />
      <Typography variant="h1" color="textPrimary" sx={{ mb: 1 }}>
        User Settings
      </Typography>
      <Typography variant="body1" color="textSecondary" sx={{ mb: 3 }}>
        Adjust application settings.
      </Typography>
      <RouteGuard>
        <Paper elevation={3} sx={{ p: { xs: 2, md: 4 } }}>
          <SettingsForm />
        </Paper>
      </RouteGuard>
      <Box sx={{ textAlign: 'center', mt: 3 }}>
        <Button component={Link} href="/" variant="contained" color="primary">Back to Home</Button>
      </Box>
    </Container>
  );
}
