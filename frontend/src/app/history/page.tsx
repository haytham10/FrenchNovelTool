'use client';

import React from 'react';
import { Box, Typography, Paper, Button, Container } from '@mui/material';
import Link from 'next/link';
import HistoryTable from '@/components/HistoryTable';
import RouteGuard from '@/components/RouteGuard';
import Breadcrumbs from '@/components/Breadcrumbs';

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
