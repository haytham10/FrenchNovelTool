'use client';

import React from 'react';
import {
  Stack,
  Card,
  CardContent,
  Typography,
  Chip,
  Box,
  LinearProgress,
} from '@mui/material';

interface ResultsKPICardsProps {
  mode: 'coverage' | 'filter' | 'batch';
  selectedCount: number | null;
  wordsCovered: number | null;
  wordsTotal: number | null;
  filterAcceptanceRatio: number | null;
  learningSetDisplayLength: number;
}

type ThemeColor = 'success' | 'warning' | 'error';

const getColorTheme = (percent: number): { color: ThemeColor; label: string; icon: string } => {
  if (percent >= 85) return { color: 'success', label: 'Excellent', icon: '✓' };
  if (percent >= 70) return { color: 'warning', label: 'Good', icon: '!' };
  return { color: 'error', label: 'Needs Work', icon: '×' };
};

export default function ResultsKPICards({
  mode,
  selectedCount,
  wordsCovered,
  wordsTotal,
  filterAcceptanceRatio,
  learningSetDisplayLength,
}: ResultsKPICardsProps) {
  const coveragePercent = wordsTotal && wordsCovered ? (wordsCovered / wordsTotal) * 100 : 0;
  const theme = getColorTheme(coveragePercent);

  return (
    <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
      {/* Sentences Selected Card */}
      <Card
        variant="outlined"
        sx={{
          flex: 1,
          borderWidth: 2,
          borderColor: 'primary.main',
          bgcolor: 'primary.50',
        }}
      >
        <CardContent sx={{ p: 3 }}>
          <Typography variant="overline" color="text.secondary" fontWeight={700} letterSpacing={1.2}>
            Sentences Selected
          </Typography>
          <Typography variant="h2" fontWeight={800} color="primary.main" sx={{ my: 1 }}>
            {mode === 'filter'
              ? (selectedCount ?? 'N/A')
              : (selectedCount ?? learningSetDisplayLength ?? 'N/A')}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            sentences in learning set
          </Typography>
        </CardContent>
      </Card>

      {mode !== 'filter' && (
        <>
          {/* Words Covered Card */}
          <Card
            variant="outlined"
            sx={{
              flex: 1,
              borderWidth: 2,
              borderColor: 'success.main',
              bgcolor: 'success.50',
            }}
          >
            <CardContent sx={{ p: 3 }}>
              <Typography variant="overline" color="text.secondary" fontWeight={700} letterSpacing={1.2}>
                Words Covered
              </Typography>
              <Typography variant="h2" fontWeight={800} color="success.main" sx={{ my: 1 }}>
                {wordsCovered ?? 'N/A'}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                of {wordsTotal ?? 'N/A'} total words
              </Typography>
            </CardContent>
          </Card>

          {/* Coverage Percentage Card with Color Coding */}
          <Card
            variant="outlined"
            sx={{
              flex: 1,
              borderWidth: 2,
              borderColor: `${theme.color}.main`,
              bgcolor: `${theme.color}.50`,
            }}
          >
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="overline" color="text.secondary" fontWeight={700} letterSpacing={1.2}>
                  Coverage
                </Typography>
                <Chip
                  label={theme.label}
                  color={theme.color}
                  size="small"
                  sx={{ fontWeight: 700 }}
                />
              </Box>
              <Typography variant="h2" fontWeight={800} color={`${theme.color}.main`} sx={{ my: 1 }}>
                {wordsTotal && wordsCovered ? `${coveragePercent.toFixed(1)}%` : 'N/A'}
              </Typography>

              {/* Visual Gauge/Progress Bar */}
              {wordsTotal && wordsCovered && (
                <Box sx={{ mt: 2 }}>
                  <LinearProgress
                    variant="determinate"
                    value={coveragePercent}
                    sx={{
                      height: 10,
                      borderRadius: 2,
                      bgcolor: 'action.hover',
                      '& .MuiLinearProgress-bar': {
                        borderRadius: 2,
                        bgcolor: `${theme.color}.main`,
                      }
                    }}
                  />
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.5 }}>
                    <Typography variant="caption" color="text.secondary">0%</Typography>
                    <Typography variant="caption" color="text.secondary">100%</Typography>
                  </Box>
                </Box>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {mode === 'filter' && (
        <Card
          variant="outlined"
          sx={{
            flex: 1,
            borderWidth: 2,
            borderColor: 'info.main',
            bgcolor: 'info.50',
          }}
        >
          <CardContent sx={{ p: 3 }}>
            <Typography variant="overline" color="text.secondary" fontWeight={700} letterSpacing={1.2}>
              Acceptance Ratio
            </Typography>
            <Typography variant="h2" fontWeight={800} color="info.main" sx={{ my: 1 }}>
              {((filterAcceptanceRatio ?? 0) * 100).toFixed(1)}%
            </Typography>
            <Typography variant="caption" color="text.secondary">
              of sentences meet criteria
            </Typography>
          </CardContent>
        </Card>
      )}
    </Stack>
  );
}
