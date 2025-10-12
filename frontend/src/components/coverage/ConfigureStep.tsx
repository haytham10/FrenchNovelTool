'use client';

import React from 'react';
import {
  Box,
  Typography,
  Paper,
  Stack,
  Select,
  MenuItem,
  FormControl,
  Button,
  Tooltip,
  IconButton,
  Slider,
  TextField,
  SelectChangeEvent,
} from '@mui/material';
import {
  Upload as UploadIcon,
  HelpOutline as HelpIcon,
} from '@mui/icons-material';
import { WordList } from '@/lib/types';

interface ConfigureStepProps {
  mode: 'coverage' | 'filter';
  setMode: (mode: 'coverage' | 'filter') => void;
  selectedWordListId: number | '';
  setSelectedWordListId: (id: number) => void;
  sentenceCap: number;
  setSentenceCap: (cap: number) => void;
  wordlists: WordList[];
  loadingWordLists: boolean;
  resolvedDefaultWordlist: WordList | null;
  uploadedFile: File | null;
  handleFileUpload: (event: React.ChangeEvent<HTMLInputElement>) => void;
  handleUploadWordList: () => void;
  uploadMutationPending: boolean;
  onShowHelp: () => void;
}

export default function ConfigureStep({
  mode,
  setMode,
  selectedWordListId,
  setSelectedWordListId,
  sentenceCap,
  setSentenceCap,
  wordlists,
  loadingWordLists,
  resolvedDefaultWordlist,
  uploadedFile,
  handleFileUpload,
  handleUploadWordList,
  uploadMutationPending,
  onShowHelp,
}: ConfigureStepProps) {
  return (
    <Box>
      <Typography variant="h5" fontWeight={600} gutterBottom>
        Configure Analysis
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
        Choose your analysis mode and target word list
      </Typography>

      <Paper elevation={0} variant="outlined" sx={{ p: 6, mt: 2, bgcolor: 'background.paper' }}>
        <Stack spacing={6} sx={{ width: 'auto', mx: 'auto' }}>
          {/* Analysis Mode */}
          <Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <Typography variant="subtitle1" fontWeight={600}>
                Analysis Mode
              </Typography>
              <Tooltip title="Click for more information about analysis modes">
                <IconButton size="small" onClick={onShowHelp}>
                  <HelpIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
            <FormControl fullWidth>
              <Select
                value={mode}
                onChange={(e: SelectChangeEvent<'coverage' | 'filter'>) =>
                  setMode(e.target.value as 'coverage' | 'filter')
                }
                displayEmpty
              >
                <MenuItem value="coverage">Coverage Mode</MenuItem>
                <MenuItem value="filter">Filter Mode</MenuItem>
              </Select>
            </FormControl>
          </Box>

          {/* Word List */}
          <Box>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Target Word List
            </Typography>
            <FormControl fullWidth>
              <Select
                value={selectedWordListId || ''}
                onChange={(e) => setSelectedWordListId(e.target.value as number)}
                disabled={loadingWordLists}
                displayEmpty
              >
                {selectedWordListId === '' && (
                  <MenuItem value="" disabled>
                    <em>Select a word list...</em>
                  </MenuItem>
                )}
                {wordlists.map((wl: WordList) => (
                  <MenuItem key={wl.id} value={wl.id}>
                    {`${wl.name} (${wl.normalized_count} words)`}
                    {(resolvedDefaultWordlist && wl.id === resolvedDefaultWordlist.id) && ' ★'}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Upload New List */}
            <Button
              component="label"
              variant="outlined"
              startIcon={<UploadIcon />}
              sx={{ mt: 2 }}
            >
              Upload New Word List (.csv)
              <input
                type="file"
                accept=".csv"
                hidden
                onChange={handleFileUpload}
              />
            </Button>

            {uploadedFile && (
              <Box sx={{ mt: 2, p: 2, bgcolor: 'action.hover', borderRadius: 1 }}>
                <Typography variant="body2" gutterBottom>{uploadedFile.name}</Typography>
                <Button
                  variant="contained"
                  onClick={handleUploadWordList}
                  disabled={uploadMutationPending}
                  size="small"
                >
                  {uploadMutationPending ? 'Confirming...' : 'Confirm Upload'}
                </Button>
              </Box>
            )}
          </Box>

          {/* Sentence Limit (for Coverage mode) */}
          {mode === 'coverage' && (
            <Box>
              <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                Learning Set Size
              </Typography>
              <Box sx={{ px: 2 }}>
                <Slider
                  value={sentenceCap === 0 ? 1000 : sentenceCap}
                  onChange={(_, value) =>
                    setSentenceCap((value as number) === 1000 ? 0 : (value as number))
                  }
                  min={50}
                  max={1000}
                  step={1}
                  marks={[
                    { value: 50, label: '50' },
                    { value: 250, label: '250' },
                    { value: 500, label: '500' },
                    { value: 700, label: '700' },
                    { value: 900, label: '900' },
                    { value: 1000, label: '∞' },
                  ]}
                  valueLabelDisplay="auto"
                  valueLabelFormat={(value) => (value === 1000 ? '∞' : value.toString())}
                />
              </Box>

              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 2 }}>
                <TextField
                  size="small"
                  value={sentenceCap === 0 ? '' : sentenceCap}
                  onChange={(e) => {
                    const raw = e.target.value.trim();
                    if (raw === '') {
                      setSentenceCap(0);
                      return;
                    }
                    const val = Number(raw);
                    if (!Number.isFinite(val)) return;
                    if (val === 1000) {
                      setSentenceCap(0);
                    } else {
                      const clamped = Math.round(Math.max(50, Math.min(999, val)));
                      setSentenceCap(clamped);
                    }
                  }}
                  type="number"
                  placeholder="Custom"
                  sx={{ width: 120 }}
                  inputProps={{ min: 50, max: 1000, step: 1 }}
                />
                <Typography variant="body2" color="text.secondary">
                  {sentenceCap === 0 ? 'Unlimited' : `${sentenceCap} sentences`}
                </Typography>
              </Box>
            </Box>
          )}
        </Stack>
      </Paper>
    </Box>
  );
}
