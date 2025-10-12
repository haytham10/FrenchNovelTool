'use client';

import React from 'react';
import {
  Card,
  CardContent,
  Box,
  Typography,
  Button,
} from '@mui/material';
import { BugReport as DiagnoseIcon } from '@mui/icons-material';

interface UncoveredWordsCardProps {
  uncoveredCount: number;
  onDiagnose: () => void;
  loading: boolean;
}

export default function UncoveredWordsCard({ uncoveredCount, onDiagnose, loading }: UncoveredWordsCardProps) {
  if (uncoveredCount === 0) {
    return null;
  }

  return (
    <Card
      variant="outlined"
      sx={{
        borderWidth: 2,
        borderColor: 'warning.main',
        bgcolor: 'warning.50',
      }}
    >
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Box>
            <Typography variant="h6" fontWeight={700} color="warning.dark" gutterBottom>
              {uncoveredCount} Words Not Covered
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Click below to see which words are missing and why
            </Typography>
          </Box>
          <DiagnoseIcon sx={{ fontSize: 48, color: 'warning.main', opacity: 0.3 }} />
        </Box>
        <Button
          variant="contained"
          color="warning"
          startIcon={<DiagnoseIcon />}
          onClick={onDiagnose}
          disabled={loading}
          fullWidth
          sx={{ fontWeight: 700 }}
        >
          View Uncovered Words Analysis
        </Button>
      </CardContent>
    </Card>
  );
}
