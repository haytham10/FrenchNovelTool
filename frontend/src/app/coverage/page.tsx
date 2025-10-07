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
  LinearProgress,
  Chip,
  Stack,
  Divider,
  SelectChangeEvent,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItemButton,
  ListItemText,
  InputAdornment,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Upload as UploadIcon,
  Search as SearchIcon,
  Download as DownloadIcon,
} from '@mui/icons-material';
import { AxiosError } from 'axios';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'next/navigation';
import { useSnackbar } from 'notistack';
import {
  listWordLists,
  createWordListFromFile,
  createCoverageRun,
  getCoverageRun,
  getProcessingHistory,
  exportCoverageRun,
  downloadCoverageRunCSV,
  type WordList,
  type CoverageRun as CoverageRunType,
  type CoverageAssignment,
} from '@/lib/api';
import RouteGuard from '@/components/RouteGuard';
import Breadcrumbs from '@/components/Breadcrumbs';
import CoverageResultsTable from '@/components/CoverageResultsTable';
import FilterResultsTable from '@/components/FilterResultsTable';
import { useSettings } from '@/lib/queries';
import { useCoverageWebSocket } from '@/lib/useCoverageWebSocket';

export default function CoveragePage() {
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const { enqueueSnackbar } = useSnackbar();
  
  // Get URL parameters for pre-filling
  const urlSource = searchParams.get('source'); // 'job' or 'history'
  const urlId = searchParams.get('id');
  const urlRunId = searchParams.get('runId'); // Pre-existing run to view
  
  // State
  const [mode, setMode] = useState<'coverage' | 'filter'>('filter');
  // Source is now only from history (UI removed for Job ID)
  const [sourceId, setSourceId] = useState<string>(urlId || '');
  const [selectedWordListId, setSelectedWordListId] = useState<number | ''>('');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [currentRunId, setCurrentRunId] = useState<number | null>(urlRunId ? parseInt(urlRunId) : null);
  const [historySearch, setHistorySearch] = useState<string>('');
  const [openSheetDialog, setOpenSheetDialog] = useState<boolean>(false);
  const [sheetUrl, setSheetUrl] = useState<string>('');
  // const [resultSearch, setResultSearch] = useState<string>('');
  const [showExportDialog, setShowExportDialog] = useState<boolean>(false);
  const [exportSheetName, setExportSheetName] = useState<string>('');
  // Load user settings to know which default wordlist is configured
  const { data: settings } = useSettings();
  
  // Update sourceId when URL params change
  useEffect(() => {
    if (urlSource && urlId) {
      setSourceId(urlId);
    }
  }, [urlSource, urlId]);
  
  // Update currentRunId when URL param changes
  useEffect(() => {
    if (urlRunId) {
      setCurrentRunId(parseInt(urlRunId));
    }
  }, [urlRunId]);
  
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
    refetchOnWindowFocus: false,
  });

  // Real-time updates via WebSocket (replace polling)
  type CoverageRunQueryData = {
    coverage_run: CoverageRunType;
    assignments?: CoverageAssignment[];
    pagination?: { page: number; per_page: number; total: number; pages: number };
  };

  const ws = useCoverageWebSocket({
    runId: currentRunId ?? null,
    enabled: !!currentRunId,
    onProgress: (run) => {
      // Update only the coverage_run in cache to keep assignments stable while processing
      queryClient.setQueryData<CoverageRunQueryData | undefined>(['coverageRun', run.id], (old) => {
        if (old) return { ...old, coverage_run: run };
        return { coverage_run: run };
      });
    },
    onComplete: (run) => {
      // Ensure final data (stats + assignments) is fetched
      queryClient.invalidateQueries({ queryKey: ['coverageRun', run.id] });
    },
  });
  // Load processing history for source selection
  const { data: historyData, isLoading: loadingHistory } = useQuery({
    queryKey: ['history', 'forCoverage'],
    queryFn: getProcessingHistory,
    staleTime: 1000 * 60 * 5,
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
        source_type: 'history',
        source_id: parseInt(sourceId),
        wordlist_id: selectedWordListId || undefined,
        config,
      });
    },
    onSuccess: (data) => {
      setCurrentRunId(data.coverage_run.id);
    },
  });
  
  const exportMutation = useMutation({
    mutationFn: async () => {
      if (!currentRunId) throw new Error('No run ID');
      return exportCoverageRun(currentRunId, exportSheetName || `Coverage Run ${currentRunId}`);
    },
    onSuccess: (data) => {
      enqueueSnackbar(`Exported to Google Sheets successfully!`, { variant: 'success' });
      if (data.spreadsheet_url) {
        window.open(data.spreadsheet_url, '_blank');
      }
      setShowExportDialog(false);
    },
    onError: (error: AxiosError | unknown) => {
      let msg = 'Export failed';
      // If this is an Axios error, try to read response.data.error safely
      if ((error as AxiosError).isAxiosError) {
        const axiosErr = error as AxiosError;
        const data = axiosErr.response?.data;
        if (data && typeof data === 'object' && 'error' in data && typeof data.error === 'string') {
          msg = data.error;
        } else if (axiosErr.message) {
          msg = axiosErr.message;
        }
      } else if (error instanceof Error) {
        msg = error.message;
      }
      enqueueSnackbar(msg, { variant: 'error' });
    },
  });
  
  const handleDownloadCSV = async () => {
    if (!currentRunId) return;
    try {
      const blob = await downloadCoverageRunCSV(currentRunId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `coverage_run_${currentRunId}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      enqueueSnackbar('CSV downloaded successfully!', { variant: 'success' });
    } catch (error: unknown) {
      let msg = 'Download failed';
      if ((error as AxiosError).isAxiosError) {
        const axiosErr = error as AxiosError;
        const data = axiosErr.response?.data;
        if (data && typeof data === 'object' && 'error' in data && typeof data.error === 'string') {
          msg = data.error;
        } else if (axiosErr.message) {
          msg = axiosErr.message;
        }
      } else if (error instanceof Error) {
        msg = error.message;
      }
      enqueueSnackbar(msg, { variant: 'error' });
    }
  };
  
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
  const history = (historyData || []).slice().sort((a, b) => (
    new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  ));

  const filteredHistory = history.filter((h) => {
    if (!historySearch) return true;
    const q = historySearch.toLowerCase().trim();
    return (
      h.original_filename?.toLowerCase().includes(q) ||
      String(h.id).includes(q) ||
      (h.job_id ? String(h.job_id).includes(q) : false)
    );
  });

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

  // Helper to safely read numeric stats from unknown stats_json
  const getNumberStat = (key: string): number | null => {
    const stats = coverageRun?.stats_json as Record<string, unknown> | undefined;
    if (!stats) return null;
    const v = stats[key];
    if (typeof v === 'number') return v;
    if (typeof v === 'string' && v.trim() !== '' && !Number.isNaN(Number(v))) return Number(v);
    return null;
  };

  // Tab state for better organization
  const [activeTab, setActiveTab] = useState<'config' | 'results'>('config');

  // Auto-switch to results tab when run completes
  useEffect(() => {
    if (coverageRun?.status === 'completed' && activeTab === 'config') {
      setActiveTab('results');
    }
  }, [coverageRun?.status, activeTab]);
  
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
          <Box>
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
            <Alert severity="info" sx={{ mt: 1 }}>
              {mode === 'filter' 
                ? '💡 Filter Mode: Prioritizes 4-word sentences (ideal for drilling), then 3-word sentences. Returns ~500 high-quality sentences with ≥95% common vocabulary.'
                : '💡 Coverage Mode: Finds the minimum number of sentences to cover every word in your list at least once. Great for comprehensive vocabulary exposure.'
              }
            </Alert>
          </Box>
          
          {/* Word List Selection */}
          <FormControl fullWidth>
            <InputLabel>Word List</InputLabel>
            <Select
              value={selectedWordListId}
              label="Word List"
              onChange={(e) => setSelectedWordListId(e.target.value as number)}
              disabled={loadingWordLists}
            >
              {wordlists.map((wl: WordList) => (
                <MenuItem key={wl.id} value={wl.id}>
                  {`${wl.name} (${wl.normalized_count} words)`}
                  {(resolvedDefaultWordlist && wl.id === resolvedDefaultWordlist.id) && (
                    <>
                      {' '}
                      (default)
                    </>
                  )}
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
          
          {/* Source Selection - From History with search */}
          <Box>
            <Typography variant="subtitle2" fontWeight={600} gutterBottom>
              Select Source (From History)
            </Typography>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }}>
              <TextField
                fullWidth
                placeholder="Search by PDF name or ID"
                value={historySearch}
                onChange={(e) => setHistorySearch(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon fontSize="small" />
                    </InputAdornment>
                  ),
                }}
              />
              <Button
                variant="outlined"
                startIcon={<UploadIcon />}
                onClick={() => setOpenSheetDialog(true)}
              >
                Import from Spreadsheet
              </Button>
            </Stack>

            <Paper variant="outlined" sx={{ maxHeight: 280, overflow: 'auto' }}>
              {loadingHistory ? (
                <Box sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                  <CircularProgress size={18} />
                  <Typography variant="body2">Loading history…</Typography>
                </Box>
              ) : filteredHistory.length === 0 ? (
                <Box sx={{ p: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    No matches. Try a different search.
                  </Typography>
                </Box>
              ) : (
                <List dense disablePadding>
                  {filteredHistory.slice(0, 100).map((h) => {
                    const selected = String(h.id) === sourceId;
                    const date = new Date(h.timestamp).toLocaleString();
                    const secondary = `ID #${h.id}${h.job_id ? ` • Job #${h.job_id}` : ''} • ${date} • ${h.processed_sentences_count} sentences`;
                    return (
                      <ListItemButton
                        key={h.id}
                        selected={selected}
                        onClick={() => setSourceId(String(h.id))}
                        sx={{
                          '&.Mui-selected': { bgcolor: 'action.selected' },
                        }}
                      >
                        <ListItemText
                          primary={h.original_filename || `History #${h.id}`}
                          secondary={secondary}
                        />
                      </ListItemButton>
                    );
                  })}
                </List>
              )}
            </Paper>
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

      {/* Import from Spreadsheet Dialog (UI stub) */}
      <Dialog open={openSheetDialog} onClose={() => setOpenSheetDialog(false)} fullWidth maxWidth="sm">
        <DialogTitle>Import from Google Sheets</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Paste a Google Sheets URL that contains a single column of sentences. This feature is planned for a future backend update.
          </Typography>
          <TextField
            fullWidth
            label="Google Sheets URL"
            placeholder="https://docs.google.com/spreadsheets/d/..."
            value={sheetUrl}
            onChange={(e) => setSheetUrl(e.target.value)}
          />
          <Alert severity="info" sx={{ mt: 2 }}>
            Coming soon: importing sentences directly from Sheets. For now, select a history entry above.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenSheetDialog(false)}>Close</Button>
          <Button disabled>Import</Button>
        </DialogActions>
      </Dialog>
      
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
                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 0.5 }}>
                    <Chip
                      label={coverageRun.status}
                      color={
                        coverageRun.status === 'completed' ? 'success' :
                        coverageRun.status === 'failed' ? 'error' :
                        coverageRun.status === 'cancelled' ? 'warning' :
                        'default'
                      }
                      size="small"
                    />
                    {coverageRun.status === 'processing' && (
                      ws.connected ? (
                        <Chip label="Live" color="success" size="small" variant="outlined" />
                      ) : (
                        <Chip label="Reconnecting..." color="warning" size="small" variant="outlined" />
                      )
                    )}
                  </Stack>
                  {/* Meta */}
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    Run #{coverageRun.id} • Mode: {coverageRun.mode} • Source: {coverageRun.source_type} #{coverageRun.source_id}
                    {coverageRun.wordlist_id ? (
                      <> • Word List: {(() => { const wl = wordlists.find((w) => w.id === coverageRun.wordlist_id); return wl ? `${wl.name} (${wl.normalized_count} words)` : `#${coverageRun.wordlist_id}`; })()}</>
                    ) : null}
                  </Typography>
                  {ws.error && (
                    <Alert severity="warning" sx={{ mt: 1 }}>
                      {ws.error.message}
                    </Alert>
                  )}
                  {coverageRun.status === 'processing' && (
                    <Box sx={{ mt: 1 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                        <Typography variant="body2" color="text.secondary">Processing…</Typography>
                        <Typography variant="body2" color="text.secondary">{coverageRun.progress_percent}%</Typography>
                      </Box>
                      <LinearProgress variant="determinate" value={coverageRun.progress_percent} />
                    </Box>
                  )}

                  <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
                    <Button variant="outlined" startIcon={<DownloadIcon />} onClick={handleDownloadCSV} disabled={!coverageRun || coverageRun.status !== 'completed'}>
                      Download CSV
                    </Button>
                    <Button variant="outlined" startIcon={<DownloadIcon />} onClick={() => setShowExportDialog(true)} disabled={!coverageRun || coverageRun.status !== 'completed'}>
                      Export to Sheets
                    </Button>
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
                              {mode === 'coverage' ? 'Word Assignments' : 'Top Sentences'}
                            </Typography>
                            
                            {/* Use dedicated table components */}
                            {mode === 'coverage' ? (
                              <CoverageResultsTable
                                assignments={assignments}
                                loading={false}
                              />
                            ) : (
                              <FilterResultsTable
                                assignments={assignments}
                                loading={false}
                              />
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
      
      {/* Export to Sheets Dialog */}
      <Dialog open={showExportDialog} onClose={() => setShowExportDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Export to Google Sheets</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Sheet Name"
            value={exportSheetName}
            onChange={(e) => setExportSheetName(e.target.value)}
            sx={{ mt: 2 }}
            placeholder="Coverage Results"
          />
          <Alert severity="info" sx={{ mt: 2 }}>
            This will create a new Google Spreadsheet with your coverage results. 
            Make sure you have connected your Google account in Settings.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowExportDialog(false)}>Cancel</Button>
          <Button 
            variant="contained" 
            onClick={() => exportMutation.mutate()}
            disabled={!exportSheetName || exportMutation.isPending}
          >
            {exportMutation.isPending ? 'Exporting...' : 'Export'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
    </RouteGuard>
  );
}
