"use client";

import React from 'react';
import { Container, Paper, Typography, Button, Box } from '@mui/material';
import Link from 'next/link';

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <Container maxWidth="lg" sx={{ py: 6 }}>
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h2" sx={{ mb: 1 }}>History failed to load</Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          {error?.message || 'Please try again.'}
        </Typography>
        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
          <Button variant="contained" onClick={reset}>Try again</Button>
          <Button variant="outlined" component={Link} href="/">Go home</Button>
        </Box>
      </Paper>
    </Container>
  );
}


