'use client';

import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Stack,
  Chip,
} from '@mui/material';

interface BatchModeSummaryProps {
  statsJson: Record<string, unknown>;
}

type SourceSummary = {
  source_id?: number | string;
  selected_sentences?: number;
  words_covered?: number;
};

export default function BatchModeSummary({ statsJson }: BatchModeSummaryProps) {
  const sourcesCount = statsJson['sources_count'] ?? 'multiple';
  const rawBreakdown = statsJson['source_breakdown'];
  const sourceBreakdown = Array.isArray(rawBreakdown) ? rawBreakdown as unknown[] : [];

  if (sourceBreakdown.length === 0) {
    return null;
  }

  return (
    <Card variant="outlined" sx={{ bgcolor: 'primary.50', borderColor: 'primary.main' }}>
      <CardContent>
        <Typography variant="h6" fontWeight={600} gutterBottom>
          Batch Analysis Summary
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Sequential processing of {String(sourcesCount)} sources
        </Typography>

        <Box sx={{ mt: 2 }}>
          <Typography variant="caption" color="text.secondary" fontWeight={600}>
            Coverage by Source:
          </Typography>
          <Stack spacing={1} sx={{ mt: 1 }}>
            {sourceBreakdown.map((s, idx) => {
              const source = s as SourceSummary;
              const selected = typeof source.selected_sentences === 'number' ? source.selected_sentences : (source.selected_sentences ?? 'N/A');
              const words = typeof source.words_covered === 'number' ? source.words_covered : (source.words_covered ?? 'N/A');
              const sid = source.source_id ?? 'unknown';

              return (
                <Box
                  key={idx}
                  sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    p: 1,
                    bgcolor: 'background.paper',
                    borderRadius: 1,
                    border: 1,
                    borderColor: 'divider'
                  }}
                >
                  <Typography variant="body2">
                    Source {idx + 1} (ID: {sid})
                  </Typography>
                  <Stack direction="row" spacing={2}>
                    <Chip
                      label={`${selected} sentences`}
                      size="small"
                      variant="outlined"
                    />
                    <Chip
                      label={`${words} new words`}
                      size="small"
                      color="success"
                    />
                  </Stack>
                </Box>
              );
            })}
          </Stack>
        </Box>
      </CardContent>
    </Card>
  );
}
