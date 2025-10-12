import React from 'react';
import { Box, Skeleton } from '@mui/material';

export default function ResultsSkeleton() {
  return (
    <Box>
      <Skeleton variant="text" height={36} width={180} sx={{ mb: 2 }} />
      {[...Array(8)].map((_, i) => (
        <Skeleton key={i} variant="rectangular" height={48} sx={{ mb: 1, borderRadius: 1 }} />
      ))}
    </Box>
  );
}


