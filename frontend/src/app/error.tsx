"use client";

import React from 'react';
import { Container, Paper, Typography, Button, Box } from '@mui/material';
import Link from 'next/link';
import Icon from '../components/Icon';
import { RotateCcw } from 'lucide-react';

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <Container maxWidth="md" sx={{ py: 8 }}>
      <Paper sx={{ p: 4, textAlign: 'center' }} elevation={3}>
        <Typography variant="h2" sx={{ mb: 1 }}>Something went wrong</Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          {error?.message || 'An unexpected error occurred.'}
        </Typography>
        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
          <Button variant="contained" onClick={reset} startIcon={<Icon icon={RotateCcw} />}>Try again</Button>
          <Button variant="outlined" component={Link} href="/">Go home</Button>
        </Box>
      </Paper>
    </Container>
  );
}


