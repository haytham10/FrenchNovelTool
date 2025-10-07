'use client';

/**
 * Coverage Run Dialog - Quick coverage run launcher from Job/History CTAs
 */
import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  Stack,
  Chip,
  SelectChangeEvent,
  CircularProgress,
} from '@mui/material';
import { PlayArrow, BookOpen } from '@mui/icons-material';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { useSnackbar } from 'notistack';
import {
  listWordLists,
  createCoverageRun,
  type WordList,
} from '@/lib/api';
import { useSettings } from '@/lib/queries';

interface CoverageRunDialogProps {
  open: boolean;
  onClose: () => void;
  sourceType: 'job' | 'history';
  sourceId: number;
  sourceName?: string;
}

export default function CoverageRunDialog({
  open,
  onClose,
  sourceType,
  sourceId,
  sourceName,
}: CoverageRunDialogProps) {
  const router = useRouter();
  const { enqueueSnackbar } = useSnackbar();
  
  const [mode, setMode] = useState<'coverage' | 'filter'>('filter');
  const [selectedWordListId, setSelectedWordListId] = useState<number | ''>('');
  
  // Load user settings to know which default wordlist is configured
  const { data: settings } = useSettings();
  
  // Load word lists
  const { data: wordListsData, isLoading: loadingWordLists } = useQuery({
    queryKey: ['wordlists'],
    queryFn: listWordLists,
    enabled: open,
  });
  
  // Create coverage run mutation
  const runMutation = useMutation({
    mutationFn: async () => {
      const config = mode === 'filter' 
        ? {
            min_in_list_ratio: 0.95,
            len_min: 4,
            len_max: 8,
            target_count: 500,
          }
        : {
            alpha: 0.5,
            beta: 0.3,
            gamma: 0.2,
          };
      
      return createCoverageRun({
        mode,
        source_type: sourceType,
        source_id: sourceId,
        wordlist_id: selectedWordListId || undefined,
        config,
      });
    },
    onSuccess: (data) => {
      enqueueSnackbar('Coverage run started successfully!', { variant: 'success' });
      onClose();
      // Navigate to coverage page with run ID
      router.push(`/coverage?runId=${data.coverage_run.id}`);
    },
    onError: (error: Error) => {
      enqueueSnackbar(`Failed to start coverage run: ${error.message}`, { variant: 'error' });
    },
  });
  
  const wordlists = wordListsData?.wordlists || [];
  
  // Determine the default word list (user default if set, else global default)
  const defaultWordlistId = settings?.default_wordlist_id ?? null;
  const resolvedDefaultWordlist = defaultWordlistId
    ? wordlists.find((wl) => wl.id === defaultWordlistId) || null
    : wordlists.find((wl) => wl.is_global_default) || null;

  // Preselect the default word list once data is available
  useEffect(() => {
    if (selectedWordListId === '' && resolvedDefaultWordlist?.id) {
      setSelectedWordListId(resolvedDefaultWordlist.id);
    }
  }, [resolvedDefaultWordlist, selectedWordListId]);
  
  const handleRun = () => {
    runMutation.mutate();
  };
  
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Stack direction="row" alignItems="center" spacing={1}>
          <BookOpen />
          <Typography variant="h6">Run Vocabulary Coverage</Typography>
        </Stack>
      </DialogTitle>
      
      <DialogContent>
        <Stack spacing={3}>
          {/* Source info */}
          <Alert severity="info" variant="outlined">
            <Typography variant="body2">
              <strong>Source:</strong> {sourceName || `${sourceType} #${sourceId}`}
            </Typography>
          </Alert>
          
          {/* Mode Selection */}
          <FormControl fullWidth>
            <InputLabel>Analysis Mode</InputLabel>
            <Select
              value={mode}
              label="Analysis Mode"
              onChange={(e: SelectChangeEvent<'coverage' | 'filter'>) => 
                setMode(e.target.value as 'coverage' | 'filter')
              }
            >
              <MenuItem value="filter">
                Filter Mode - High-density vocabulary sentences
              </MenuItem>
              <MenuItem value="coverage">
                Coverage Mode - Minimal set covering all words
              </MenuItem>
            </Select>
          </FormControl>
          
          <Alert severity="info" variant="standard">
            {mode === 'filter' 
              ? '💡 Filter Mode: Prioritizes 4-word sentences (ideal for drilling), then 3-word sentences. Returns ~500 high-quality sentences with ≥95% common vocabulary.'
              : '💡 Coverage Mode: Finds the minimum number of sentences to cover every word in your list at least once.'
            }
          </Alert>
          
          {/* Word List Selection */}
          <FormControl fullWidth>
            <InputLabel>Word List</InputLabel>
            <Select
              value={selectedWordListId}
              label="Word List"
              onChange={(e) => setSelectedWordListId(e.target.value as number)}
              disabled={loadingWordLists}
            >
              {loadingWordLists ? (
                <MenuItem value="">
                  <CircularProgress size={20} sx={{ mr: 1 }} />
                  Loading...
                </MenuItem>
              ) : (
                <>
                  <MenuItem value="">
                    <em>Use default word list</em>
                  </MenuItem>
                  {wordlists.map((wl: WordList) => (
                    <MenuItem key={wl.id} value={wl.id}>
                      {`${wl.name} (${wl.normalized_count} words)`}
                      {(resolvedDefaultWordlist && wl.id === resolvedDefaultWordlist.id) && (
                        <Chip label="default" size="small" sx={{ ml: 1 }} />
                      )}
                    </MenuItem>
                  ))}
                </>
              )}
            </Select>
          </FormControl>
          
          {runMutation.isError && (
            <Alert severity="error">
              Failed to start coverage run. Please try again.
            </Alert>
          )}
        </Stack>
      </DialogContent>
      
      <DialogActions>
        <Button onClick={onClose} disabled={runMutation.isPending}>
          Cancel
        </Button>
        <Button
          variant="contained"
          startIcon={runMutation.isPending ? <CircularProgress size={20} /> : <PlayArrow />}
          onClick={handleRun}
          disabled={runMutation.isPending || loadingWordLists}
        >
          {runMutation.isPending ? 'Starting...' : 'Run Coverage'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
