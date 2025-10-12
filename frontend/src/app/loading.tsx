import React from 'react';
import { Container, Box, Skeleton, Paper } from '@mui/material';

export default function Loading() {
  return (
    <Container maxWidth="lg" sx={{ py: 8 }}>
      <Box sx={{ textAlign: 'center', mb: 6 }}>
        <Skeleton variant="text" sx={{ mx: 'auto', width: { xs: '70%', md: 500 }, height: 56 }} />
        <Skeleton variant="text" sx={{ mx: 'auto', width: { xs: '90%', md: 600 } }} />
      </Box>
      <Paper sx={{ p: { xs: 2, md: 4 } }}>
        <Skeleton variant="rectangular" height={160} />
      </Paper>
    </Container>
  );
}


