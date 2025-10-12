'use client';

import React from 'react';
import {
  Paper,
  Typography,
  Stack,
  Box,
} from '@mui/material';

export default function InfoPanel() {
  return (
    <Paper sx={{ p: 3, mt: 3, bgcolor: 'background.default' }}>
      <Typography variant="h6" gutterBottom>
        About Coverage Modes
      </Typography>

      <Stack spacing={2}>
        <Box>
          <Typography variant="subtitle2" gutterBottom>
            Coverage Mode (Comprehensive Learning)
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Selects a minimal set of sentences that covers all vocabulary words in your list,
            prioritizing shorter sentences with more content words. Focuses on nouns, verbs, adjectives,
            and adverbs while ignoring function words. Useful for ensuring complete vocabulary exposure.
          </Typography>
        </Box>

        <Box>
          <Typography variant="subtitle2" gutterBottom>
            Filter Mode (Recommended for Drilling)
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Finds sentences with at least 4 vocabulary words (nouns, verbs, adjectives, adverbs) from your list
            and 4-8 words in length. Ignores &ldquo;glue words&rdquo; like pronouns, determiners, and conjunctions.
            Perfect for creating high-quality sentences for daily repetition drills.
          </Typography>
        </Box>
      </Stack>
    </Paper>
  );
}
