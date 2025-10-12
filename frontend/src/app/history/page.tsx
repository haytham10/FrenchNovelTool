'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import { Box, Typography, Paper, Button, Container, Skeleton } from '@mui/material';
import Link from 'next/link';
import RouteGuard from '@/components/RouteGuard';
import Breadcrumbs from '@/components/Breadcrumbs';

// Lazy load the heavy HistoryTable component
const HistoryTable = dynamic(() => import('@/components/HistoryTable'), {
  loading: () => (
    <Box>
      {[...Array(8)].map((_, i) => (
        <Skeleton key={i} variant="rectangular" height={48} sx={{ mb: 1 }} />
      ))}
    </Box>
  ),
  ssr: false,
});

export default function HistoryPage() {
  return (
    <Container maxWidth="lg" sx={{ py: 6 }}>
      <Breadcrumbs items={[{ label: 'Home', href: '/' }, { label: 'History' }]} />
      <Typography variant="h1" color="textPrimary" sx={{ mb: 1 }}>
        Processing History
      </Typography>
      <Typography variant="body1" color="textSecondary" sx={{ mb: 3 }}>
        View your past PDF processing and export activities.
      </Typography>
      <RouteGuard>
        <Paper elevation={3} sx={{ p: { xs: 2, md: 4 } }}>
          <HistoryTable />
        </Paper>
      </RouteGuard>
      <Box sx={{ textAlign: 'center', mt: 3 }}>
        <Button component={Link} href="/" variant="contained" color="primary">Back to Home</Button>
      </Box>
    </Container>
  );
}
