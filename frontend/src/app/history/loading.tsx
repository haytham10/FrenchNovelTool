import React from 'react';
import { Container, Skeleton, Paper } from '@mui/material';

export default function Loading() {
  return (
    <Container maxWidth="lg" sx={{ py: 6 }}>
      <Skeleton variant="text" height={48} width={320} />
      <Skeleton variant="text" width={480} />
      <Paper sx={{ p: 2, mt: 2 }}>
        {[...Array(8)].map((_, i) => (
          <Skeleton key={i} variant="rectangular" height={48} sx={{ mb: 1 }} />
        ))}
      </Paper>
    </Container>
  );
}


