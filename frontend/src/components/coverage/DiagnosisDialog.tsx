'use client';

import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Stack,
  Chip,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Divider,
} from '@mui/material';
import { BugReport as DiagnoseIcon } from '@mui/icons-material';
import { CoverageDiagnosis } from '@/lib/api';

interface DiagnosisDialogProps {
  open: boolean;
  onClose: () => void;
  loading: boolean;
  diagnosisData: CoverageDiagnosis | null;
}

type ThemeColor = 'success' | 'warning' | 'error';

const getColorTheme = (percent: number): { color: ThemeColor } => {
  if (percent >= 85) return { color: 'success' };
  if (percent >= 70) return { color: 'warning' };
  return { color: 'error' };
};

export default function DiagnosisDialog({
  open,
  onClose,
  loading,
  diagnosisData,
}: DiagnosisDialogProps) {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      scroll="paper"
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <DiagnoseIcon color="primary" />
          <Typography variant="h6">Coverage Diagnosis</Typography>
        </Box>
      </DialogTitle>
      <DialogContent dividers>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', py: 8 }}>
            <CircularProgress />
            <Typography variant="body1" sx={{ ml: 2 }}>Analyzing uncovered words...</Typography>
          </Box>
        ) : diagnosisData ? (
          <Stack spacing={3}>
            {/* Summary Stats */}
            <Box>
              <Typography variant="h6" gutterBottom>
                Coverage Summary
              </Typography>
              <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
                <Chip
                  label={`${diagnosisData.covered_words} / ${diagnosisData.total_words} words`}
                  color="success"
                  size="medium"
                />
                <Chip
                  label={`${diagnosisData.coverage_percentage.toFixed(1)}% coverage`}
                  color={getColorTheme(diagnosisData.coverage_percentage).color}
                  size="medium"
                />
                <Chip
                  label={`${diagnosisData.uncovered_words} uncovered`}
                  color="warning"
                  size="medium"
                />
              </Stack>
            </Box>

            {/* Recommendation */}
            <Alert severity="info" sx={{ '& .MuiAlert-message': { width: '100%' } }}>
              <Typography variant="body2">
                <strong>Recommendation:</strong> {diagnosisData.recommendation}
              </Typography>
            </Alert>

            <Divider />

            {/* Category Breakdown */}
            <Typography variant="h6" gutterBottom>
              Uncovered Words Breakdown
            </Typography>

            {Object.entries(diagnosisData.categories).map(([key, category]) => (
              <Card key={key} variant="outlined">
                <CardContent>
                  <Typography variant="subtitle1" fontWeight={600} gutterBottom color="primary.main">
                    {category.description}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    <strong>Count:</strong> {category.count} words
                  </Typography>
                  {category.sample_words.length > 0 && (
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="caption" color="text.secondary" gutterBottom display="block">
                        Sample words (showing up to {category.sample_words.length}):
                      </Typography>
                      <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {category.sample_words.map((word, idx) => (
                          <Chip
                            key={idx}
                            label={word}
                            size="small"
                            variant="outlined"
                            sx={{ fontFamily: 'monospace' }}
                          />
                        ))}
                      </Box>
                    </Box>
                  )}
                </CardContent>
              </Card>
            ))}
          </Stack>
        ) : (
          <Typography color="text.secondary">No diagnosis data available</Typography>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} variant="contained">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
}
