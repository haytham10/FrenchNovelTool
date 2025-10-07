'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Paper,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  CircularProgress,
  Chip,
  Stack,
  Divider,
  SelectChangeEvent,
  Tabs,
  Tab,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Upload as UploadIcon,
  History as HistoryIcon,
  WorkOutline as JobIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'next/navigation';
import {
  listWordLists,
  createWordListFromFile,
  createCoverageRun,
  getCoverageRun,
  type WordList,
  type CoverageAssignment,
} from '@/lib/api';
import RouteGuard from '@/components/RouteGuard';
import Breadcrumbs from '@/components/Breadcrumbs';

export default function CoveragePage() {
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  
  // Get URL parameters for pre-filling
  const urlSource = searchParams.get('source'); // 'job' or 'history'
  const urlId = searchParams.get('id');
  
  // State
  const [mode, setMode] = useState<'coverage' | 'filter'>('filter');
  const [sourceType, setSourceType] = useState<'job' | 'history'>(urlSource === 'job' ? 'job' : 'history');
  const [sourceId, setSourceId] = useState<string>(urlId || '');
  const [selectedWordListId, setSelectedWordListId] = useState<number | ''>('');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [currentRunId, setCurrentRunId] = useState<number | null>(null);
  
  // Update sourceId when URL params change
  useEffect(() => {
    if (urlSource && urlId) {
      setSourceType(urlSource === 'job' ? 'job' : 'history');
      setSourceId(urlId);
    }
  }, [urlSource, urlId]);
  
  // Load word lists
  const { data: wordListsData, isLoading: loadingWordLists } = useQuery({
    queryKey: ['wordlists'],
    queryFn: listWordLists,
  });
  
  // Load coverage run results
  const { data: runData, isLoading: loadingRun } = useQuery({
    queryKey: ['coverageRun', currentRunId],
    queryFn: () => getCoverageRun(currentRunId!),
    enabled: !!currentRunId,
    refetchInterval: () => {
      // Poll if still processing - use queryClient to read current cached data to avoid incorrect typing of the callback param
      if (!currentRunId) return false;
      const cached = queryClient.getQueryData(['coverageRun', currentRunId]) as { coverage_run?: { status?: string } } | undefined;
      const status = cached?.coverage_run?.status;
      if (status === 'processing' || status === 'pending') {
        return 2000; // Poll every 2 seconds
      }
      return false; // Stop polling when complete
    },
  });
  
  // Upload word list mutation
  const uploadMutation = useMutation({
    mutationFn: async (data: { file: File; name: string }) => {
      return createWordListFromFile(data.file, data.name, true);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['wordlists'] });
      setSelectedWordListId(data.wordlist.id);
      setUploadedFile(null);
    },
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
        source_id: parseInt(sourceId),
        wordlist_id: selectedWordListId || undefined,
        config,
      });
    },
    onSuccess: (data) => {
      setCurrentRunId(data.coverage_run.id);
    },
  });
  
  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setUploadedFile(file);
    }
  };
  
  const handleUploadWordList = () => {
    if (uploadedFile) {
      uploadMutation.mutate({
        file: uploadedFile,
        name: uploadedFile.name.replace('.csv', ''),
      });
    }
  };
  
  const handleRunCoverage = () => {
    if (sourceId) {
      runMutation.mutate();
    }
  };
  
  const wordlists = wordListsData?.wordlists || [];
  const coverageRun = runData?.coverage_run;
  const assignments = runData?.assignments || [];

  // Helper to safely read numeric stats from unknown stats_json
  const getNumberStat = (key: string): number | null => {
    const stats = coverageRun?.stats_json as Record<string, unknown> | undefined;
    if (!stats) return null;
    const v = stats[key];
    if (typeof v === 'number') return v;
    if (typeof v === 'string' && v.trim() !== '' && !Number.isNaN(Number(v))) return Number(v);
    return null;
  };
  
  return (
    <RouteGuard>
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Breadcrumbs items={[{ label: 'Home', href: '/' }, { label: 'Vocabulary Coverage' }]} />
        
        <Typography variant="h3" component="h1" gutterBottom sx={{ mb: 1 }}>
          Vocabulary Coverage Tool
        </Typography>
        
        <Typography variant="body1" color="text.secondary" paragraph sx={{ mb: 4 }}>
          Analyze sentences based on high-frequency vocabulary. Perfect for creating optimized language learning materials.
        </Typography>
        
      {/* Configuration Panel */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h5" gutterBottom>
          Configuration
        </Typography>
        
        <Stack spacing={3}>
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
                Filter Mode - Find high-density vocabulary sentences (recommended)
              </MenuItem>
              <MenuItem value="coverage">
                Coverage Mode - Minimal set covering all words
              </MenuItem>
            </Select>
          </FormControl>
          
          {/* Word List Selection */}
          <FormControl fullWidth>
            <InputLabel>Word List</InputLabel>
            <Select
              value={selectedWordListId}
              label="Word List"
              onChange={(e) => setSelectedWordListId(e.target.value as number)}
              disabled={loadingWordLists}
            >
              <MenuItem value="">
                <em>Use default</em>
              </MenuItem>
              {wordlists.map((wl: WordList) => (
                <MenuItem key={wl.id} value={wl.id}>
                  {wl.name} ({wl.normalized_count} words)
                  {wl.is_global_default && <Chip label="Default" size="small" sx={{ ml: 1 }} />}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          
          {/* Upload Word List */}
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Or upload a new word list (CSV):
            </Typography>
            <Stack direction="row" spacing={2} alignItems="center">
              <Button
                component="label"
                variant="outlined"
                startIcon={<UploadIcon />}
              >
                Choose File
                <input
                  type="file"
                  accept=".csv"
                  hidden
                  onChange={handleFileUpload}
                />
              </Button>
              {uploadedFile && (
                <>
                  <Typography variant="body2">{uploadedFile.name}</Typography>
                  <Button
                    variant="contained"
                    onClick={handleUploadWordList}
                    disabled={uploadMutation.isPending}
                  >
                    {uploadMutation.isPending ? 'Uploading...' : 'Upload'}
                  </Button>
                </>
              )}
            </Stack>
            {uploadMutation.isError && (
              <Alert severity="error" sx={{ mt: 1 }}>
                Failed to upload word list
              </Alert>
            )}
          </Box>
          
          <Divider />
          
          {/* Source Selection */}
          <Box>
            <Typography variant="subtitle2" fontWeight={600} gutterBottom>
              Select Source
            </Typography>
            <Tabs
              value={sourceType}
              onChange={(_, newValue) => setSourceType(newValue as 'job' | 'history')}
              sx={{ mb: 2, borderBottom: 1, borderColor: 'divider' }}
            >
              <Tab icon={<HistoryIcon />} iconPosition="start" label="From History" value="history" />
              <Tab icon={<JobIcon />} iconPosition="start" label="From Job ID" value="job" />
            </Tabs>
            
            <TextField
              fullWidth
              label={`${sourceType === 'job' ? 'Job' : 'History Entry'} ID`}
              value={sourceId}
              onChange={(e) => setSourceId(e.target.value)}
              type="number"
              helperText={urlSource && urlId ? "Pre-filled from previous page" : `Enter the ID of the ${sourceType === 'job' ? 'job' : 'history entry'} to analyze`}
              size="medium"
            />
          </Box>
          
          {/* Run Button */}
          <Button
            variant="contained"
            size="large"
            startIcon={<PlayIcon />}
            onClick={handleRunCoverage}
            disabled={!sourceId || runMutation.isPending}
            fullWidth
            sx={{ mt: 1 }}
          >
            {runMutation.isPending ? 'Starting Analysis...' : 'Run Vocabulary Coverage'}
          </Button>
          
          {runMutation.isError && (
            <Alert severity="error">
              Failed to start coverage run. Please check your inputs.
            </Alert>
          )}
        </Stack>
      </Paper>
      
      {/* Results Panel */}
      {(loadingRun || coverageRun) && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h5" gutterBottom>
            Results
          </Typography>
          
          <Stack spacing={2}>
            {/* Status */}
            <Box>
              {loadingRun && !coverageRun && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  <CircularProgress size={20} />
                  <Typography variant="body2">Loading run...</Typography>
                </Box>
              )}

              {coverageRun ? (
                <>
                  <Typography variant="subtitle2">Status:</Typography>
                  <Chip
                    label={coverageRun.status}
                    color={
                      coverageRun.status === 'completed' ? 'success' :
                      coverageRun.status === 'failed' ? 'error' :
                      'default'
                    }
                    sx={{ mt: 0.5 }}
                  />
                  {coverageRun.status === 'processing' && (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                      <CircularProgress size={20} />
                      <Typography variant="body2">
                        Processing... {coverageRun.progress_percent}%
                      </Typography>
                    </Box>
                  )}

                  {/* Stats */}
                  {coverageRun.status === 'completed' && coverageRun.stats_json && (
                    <>
                      <Divider />
                      <Box>
                        <Typography variant="subtitle2" gutterBottom>
                          Statistics:
                        </Typography>
                        {mode === 'filter' ? (
                          <Stack spacing={1}>
                            <Typography variant="body2">
                              Total sentences: {getNumberStat('total_sentences') ?? 'N/A'}
                            </Typography>
                            <Typography variant="body2">
                              Passed filter: {getNumberStat('candidates_passed_filter') ?? 'N/A'}
                            </Typography>
                            <Typography variant="body2">
                              Selected: {getNumberStat('selected_count') ?? 'N/A'}
                            </Typography>
                            <Typography variant="body2">
                              Acceptance ratio: {((getNumberStat('filter_acceptance_ratio') ?? 0) * 100).toFixed(1)}%
                            </Typography>
                          </Stack>
                        ) : (
                          <Stack spacing={1}>
                            <Typography variant="body2">
                              Total words: {getNumberStat('words_total') ?? 'N/A'}
                            </Typography>
                            <Typography variant="body2">
                              Covered: {getNumberStat('words_covered') ?? 'N/A'}
                            </Typography>
                            <Typography variant="body2">
                              Uncovered: {getNumberStat('words_uncovered') ?? 'N/A'}
                            </Typography>
                            <Typography variant="body2">
                              Selected sentences: {getNumberStat('selected_sentence_count') ?? 'N/A'}
                            </Typography>
                          </Stack>
                        )}
                      </Box>

                      {/* Sample Results */}
                      {assignments.length > 0 && (
                        <>
                          <Divider />
                          <Box>
                            <Typography variant="subtitle2" gutterBottom>
                              Sample Results (first 10):
                            </Typography>
                            <Stack spacing={1}>
                              {assignments.slice(0, 10).map((assignment: CoverageAssignment, idx: number) => (
                                <Paper key={idx} variant="outlined" sx={{ p: 1.5 }}>
                                  <Typography variant="body2" fontWeight="medium">
                                    {assignment.sentence_text}
                                  </Typography>
                                  <Typography variant="caption" color="text.secondary">
                                    {mode === 'coverage' 
                                      ? `Word: ${assignment.word_key}`
                                      : `Score: ${assignment.sentence_score ? assignment.sentence_score.toFixed(2) : 'N/A'}`
                                    }
                                  </Typography>
                                </Paper>
                              ))}
                            </Stack>

                            {assignments.length > 10 && (
                              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                                ... and {assignments.length - 10} more results
                              </Typography>
                            )}
                          </Box>
                        </>
                      )}
                    </>
                  )}

                  {/* Error */}
                  {coverageRun.status === 'failed' && coverageRun.error_message && (
                    <Alert severity="error">
                      {coverageRun.error_message}
                    </Alert>
                  )}
                </>
              ) : null}
            </Box>
          </Stack>
        </Paper>
      )}
      
      {/* Info Panel */}
      <Paper sx={{ p: 3, mt: 3, bgcolor: 'background.default' }}>
        <Typography variant="h6" gutterBottom>
          About Coverage Modes
        </Typography>
        
        <Stack spacing={2}>
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Filter Mode (Recommended for Drilling)
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Finds sentences with high vocabulary density (≥95% common words) and 4-8 words in length. 
              Perfect for creating ~500 high-quality sentences for daily repetition drills.
            </Typography>
          </Box>
          
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Coverage Mode (Comprehensive Learning)
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Selects a minimal set of sentences that covers all words in your vocabulary list. 
              Useful for ensuring complete vocabulary exposure.
            </Typography>
          </Box>
        </Stack>
      </Paper>
    </Container>
    </RouteGuard>
  );
}
