'use client';

import React, { useState } from 'react';
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
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Upload as UploadIcon,
  Download as DownloadIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listWordLists,
  createWordListFromFile,
  createCoverageRun,
  getCoverageRun,
  type WordList,
  type CoverageRun as CoverageRunType,
} from '@/lib/api';

export default function CoveragePage() {
  const queryClient = useQueryClient();
  
  // State
  const [mode, setMode] = useState<'coverage' | 'filter'>('filter');
  const [sourceType, setSourceType] = useState<'job' | 'history'>('history');
  const [sourceId, setSourceId] = useState<string>('');
  const [selectedWordListId, setSelectedWordListId] = useState<number | ''>('');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [currentRunId, setCurrentRunId] = useState<number | null>(null);
  
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
    refetchInterval: (data) => {
      // Poll if still processing
      if (data?.coverage_run?.status === 'processing' || data?.coverage_run?.status === 'pending') {
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
  
  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h3" component="h1" gutterBottom>
        Vocabulary Coverage Tool
      </Typography>
      
      <Typography variant="body1" color="text.secondary" paragraph>
        Analyze sentences based on high-frequency vocabulary. Select a mode, word list, and source to get started.
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
          <FormControl fullWidth>
            <InputLabel>Source Type</InputLabel>
            <Select
              value={sourceType}
              label="Source Type"
              onChange={(e: SelectChangeEvent<'job' | 'history'>) =>
                setSourceType(e.target.value as 'job' | 'history')
              }
            >
              <MenuItem value="history">History Entry</MenuItem>
              <MenuItem value="job">Job</MenuItem>
            </Select>
          </FormControl>
          
          <TextField
            fullWidth
            label={`${sourceType === 'job' ? 'Job' : 'History Entry'} ID`}
            value={sourceId}
            onChange={(e) => setSourceId(e.target.value)}
            type="number"
            helperText="Enter the ID of the job or history entry to analyze"
          />
          
          {/* Run Button */}
          <Button
            variant="contained"
            size="large"
            startIcon={<PlayIcon />}
            onClick={handleRunCoverage}
            disabled={!sourceId || runMutation.isPending}
            fullWidth
          >
            {runMutation.isPending ? 'Starting...' : 'Run Coverage Analysis'}
          </Button>
          
          {runMutation.isError && (
            <Alert severity="error">
              Failed to start coverage run. Please check your inputs.
            </Alert>
          )}
        </Stack>
      </Paper>
      
      {/* Results Panel */}
      {coverageRun && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h5" gutterBottom>
            Results
          </Typography>
          
          <Stack spacing={2}>
            {/* Status */}
            <Box>
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
            </Box>
            
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
                        Total sentences: {coverageRun.stats_json.total_sentences}
                      </Typography>
                      <Typography variant="body2">
                        Passed filter: {coverageRun.stats_json.candidates_passed_filter}
                      </Typography>
                      <Typography variant="body2">
                        Selected: {coverageRun.stats_json.selected_count}
                      </Typography>
                      <Typography variant="body2">
                        Acceptance ratio: {(coverageRun.stats_json.filter_acceptance_ratio * 100).toFixed(1)}%
                      </Typography>
                    </Stack>
                  ) : (
                    <Stack spacing={1}>
                      <Typography variant="body2">
                        Total words: {coverageRun.stats_json.words_total}
                      </Typography>
                      <Typography variant="body2">
                        Covered: {coverageRun.stats_json.words_covered}
                      </Typography>
                      <Typography variant="body2">
                        Uncovered: {coverageRun.stats_json.words_uncovered}
                      </Typography>
                      <Typography variant="body2">
                        Selected sentences: {coverageRun.stats_json.selected_sentence_count}
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
                        {assignments.slice(0, 10).map((assignment, idx) => (
                          <Paper key={idx} variant="outlined" sx={{ p: 1.5 }}>
                            <Typography variant="body2" fontWeight="medium">
                              {assignment.sentence_text}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {mode === 'coverage' 
                                ? `Word: ${assignment.word_key}`
                                : `Score: ${assignment.sentence_score?.toFixed(2)}`
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
  );
}
