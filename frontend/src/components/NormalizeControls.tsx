'use client';

import React from 'react';
import { Box, Typography, Slider, Paper, Chip, Stack } from '@mui/material';
import Icon from './Icon';
import { Sliders } from 'lucide-react';

interface NormalizeControlsProps {
  sentenceLength: number;
  onSentenceLengthChange: (value: number) => void;
  disabled?: boolean;
}

const PRESETS = [
  { label: 'Short', value: 8 },
  { label: 'Medium', value: 12 },
  { label: 'Long', value: 16 },
];

export default function NormalizeControls({
  sentenceLength,
  onSentenceLengthChange,
  disabled = false,
}: NormalizeControlsProps) {
  return (
    <Paper elevation={0} sx={{ p: 3, bgcolor: 'background.paper', border: 1, borderColor: 'divider' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <Icon icon={Sliders} color="primary" />
        <Typography variant="h6" fontWeight={600}>
          Sentence Length Settings
        </Typography>
      </Box>
      
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Adjust the target sentence length for normalization. Shorter sentences are easier to read but may lose some context.
      </Typography>

      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle2" gutterBottom>
          Target Length: <strong>{sentenceLength} words</strong>
        </Typography>
        <Slider
          value={sentenceLength}
          onChange={(_, value) => onSentenceLengthChange(value as number)}
          min={5}
          max={20}
          step={1}
          marks={[
            { value: 5, label: '5' },
            { value: 10, label: '10' },
            { value: 15, label: '15' },
            { value: 20, label: '20' },
          ]}
          disabled={disabled}
          valueLabelDisplay="auto"
          sx={{ mt: 2 }}
        />
      </Box>

      <Box>
        <Typography variant="subtitle2" gutterBottom>
          Quick Presets
        </Typography>
        <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
          {PRESETS.map((preset) => (
            <Chip
              key={preset.value}
              label={`${preset.label} (${preset.value})`}
              onClick={() => onSentenceLengthChange(preset.value)}
              color={sentenceLength === preset.value ? 'primary' : 'default'}
              variant={sentenceLength === preset.value ? 'filled' : 'outlined'}
              disabled={disabled}
              clickable
            />
          ))}
        </Stack>
      </Box>
    </Paper>
  );
}
