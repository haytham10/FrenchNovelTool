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
  Slider,
  Card,
  CardContent,
  CardActionArea,
  IconButton,
  Tooltip,
  Radio,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Upload as UploadIcon,
  Search as SearchIcon,
  Download as DownloadIcon,
  HelpOutline as HelpIcon,
  Description as PdfIcon,
  TableChart as SheetsIcon,
  Cancel as CancelIcon,
  CloudUpload as CloudUploadIcon,
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
  importSentencesFromSheets,
  getCoverageCost,
  getCredits,
  type WordList,
  type CoverageRun as CoverageRunType,
  type CoverageAssignment,
  type LearningSetEntry,
} from '@/lib/api';
import RouteGuard from '@/components/RouteGuard';
import Breadcrumbs from '@/components/Breadcrumbs';
import LearningSetTable from '@/components/LearningSetTable';
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
  const [sentenceCap, setSentenceCap] = useState<number>(500); // Coverage mode sentence cap (0 = unlimited)
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
  
  // Load coverage cost
  const { data: costData } = useQuery({
    queryKey: ['coverageCost'],
    queryFn: getCoverageCost,
    staleTime: 1000 * 60 * 60, // Cache for 1 hour
  });
  
  // Load user credits
  const { data: creditsData } = useQuery({
    queryKey: ['credits'],
    queryFn: getCredits,
    staleTime: 1000 * 60, // Refresh every minute
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
    learning_set?: LearningSetEntry[];
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
  
  // Import from Google Sheets mutation
  const importSheetsMutation = useMutation({
    mutationFn: async (sheetUrl: string) => {
      return importSentencesFromSheets(sheetUrl);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['history', 'forCoverage'] });
      setSourceId(String(data.history_id));
      setOpenSheetDialog(false);
      setSheetUrl('');
      enqueueSnackbar(
        `Imported ${data.sentence_count} sentences from ${data.filename}`,
        { variant: 'success' }
      );
    },
    onError: (error: Error) => {
      enqueueSnackbar(
        `Failed to import from Google Sheets: ${error.message}`,
        { variant: 'error' }
      );
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
            target_count: sentenceCap, // Use user-selected sentence cap
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
      queryClient.invalidateQueries({ queryKey: ['credits'] }); // Refresh credit balance
      enqueueSnackbar(
        `Coverage run started! ${data.credits_charged} credits charged.`,
        { variant: 'success' }
      );
    },
    onError: (error: unknown) => {
      let msg = 'Failed to start coverage run';
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
  const assignments = React.useMemo(
    () => runData?.assignments ?? [],
    [runData?.assignments]
  );
  const learningSet = React.useMemo(
    () => ((runData?.learning_set as LearningSetEntry[] | undefined) ?? []),
    [runData?.learning_set]
  );
  const learningSetDisplay = React.useMemo(() => {
    if (learningSet.length > 0) return learningSet;
    if (assignments.length === 0) return [] as LearningSetEntry[];

    const unique = new Map<number, string>();
    assignments.forEach((assignment) => {
      if (!unique.has(assignment.sentence_index)) {
        unique.set(assignment.sentence_index, assignment.sentence_text);
      }
    });

    return Array.from(unique.entries())
      .sort((a, b) => a[0] - b[0])
      .map(([sentenceIndex, sentenceText], idx) => ({
        rank: idx + 1,
        sentence_index: sentenceIndex,
        sentence_text: sentenceText,
        token_count: null,
        new_word_count: null,
        score: null,
      }));
  }, [learningSet, assignments]);
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

  // Help dialog state
  const [showHelpDialog, setShowHelpDialog] = useState(false);
  
  return (
    <RouteGuard>
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Breadcrumbs items={[{ label: 'Home', href: '/' }, { label: 'Vocabulary Coverage' }]} />
        
        <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Typography variant="h3" component="h1" gutterBottom sx={{ mb: 1 }}>
              Vocabulary Coverage Tool
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Analyze sentences based on high-frequency vocabulary. Perfect for creating optimized language learning materials.
            </Typography>
          </Box>
        </Box>
        
      {/* Three-Column Wizard Layout */}
      <Box sx={{ 
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', md: 'repeat(3, 1fr)' },
        gap: 3,
        minHeight: '70vh',
      }}>
        {/* COLUMN 1: CONFIGURE */}
        <Box>
          <Paper sx={{ p: 3, height: '100%', position: 'sticky', top: 80 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
              <Chip label="1" color="primary" size="small" />
              <Typography variant="h6" fontWeight={600}>
                Configure Analysis
              </Typography>
            </Box>
            
            <Stack spacing={3}>
              {/* Analysis Mode */}
              <Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <Typography variant="subtitle2" fontWeight={600}>
                    Analysis Mode
                  </Typography>
                  <Tooltip title="Click for more information about analysis modes">
                    <IconButton size="small" onClick={() => setShowHelpDialog(true)}>
                      <HelpIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Box>
                <FormControl fullWidth size="small">
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
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Target Word List
                </Typography>
                <FormControl fullWidth size="small">
                  <Select
                    value={selectedWordListId}
                    onChange={(e) => setSelectedWordListId(e.target.value as number)}
                    disabled={loadingWordLists}
                    displayEmpty
                  >
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
                  variant="text"
                  size="small"
                  startIcon={<UploadIcon />}
                  fullWidth
                  sx={{ mt: 1, justifyContent: 'flex-start' }}
                >
                  + Upload New List (.csv)
                  <input
                    type="file"
                    accept=".csv"
                    hidden
                    onChange={handleFileUpload}
                  />
                </Button>
                
                {uploadedFile && (
                  <Box sx={{ mt: 1, p: 1, bgcolor: 'action.hover', borderRadius: 1 }}>
                    <Typography variant="caption" display="block">{uploadedFile.name}</Typography>
                    <Button
                      size="small"
                      variant="contained"
                      onClick={handleUploadWordList}
                      disabled={uploadMutation.isPending}
                      sx={{ mt: 0.5 }}
                    >
                      {uploadMutation.isPending ? 'Uploading...' : 'Upload'}
                    </Button>
                  </Box>
                )}
              </Box>
              
              {/* Sentence Limit (for Coverage mode) */}
              {mode === 'coverage' && (
                <Box>
                  <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                    Learning Set Size
                  </Typography>
                  <Box sx={{ px: 1 }}>
                    <Slider
                      value={sentenceCap === 0 ? 1000 : sentenceCap}
                      onChange={(_, value) => setSentenceCap(value as number === 1000 ? 0 : value as number)}
                      min={100}
                      max={1000}
                      step={null}
                      marks={[
                        { value: 100, label: '100' },
                        { value: 250, label: '250' },
                        { value: 500, label: '500' },
                        { value: 1000, label: '∞' },
                      ]}
                      valueLabelDisplay="auto"
                      valueLabelFormat={(value) => value === 1000 ? '∞' : value.toString()}
                    />
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1 }}>
                    <TextField
                      size="small"
                      value={sentenceCap === 0 ? '' : sentenceCap}
                      onChange={(e) => {
                        const val = parseInt(e.target.value);
                        if (!isNaN(val) && val >= 50 && val <= 999) {
                          setSentenceCap(val);
                        }
                      }}
                      type="number"
                      placeholder="Custom"
                      sx={{ width: 100 }}
                      inputProps={{ min: 50, max: 999 }}
                    />
                    <Typography variant="caption" color="text.secondary">
                      {sentenceCap === 0 ? 'Unlimited' : `${sentenceCap} sentences`}
                    </Typography>
                  </Box>
                </Box>
              )}
            </Stack>
          </Paper>
        </Box>
        
        {/* COLUMN 2: SELECT SOURCE */}
        <Box>
          <Paper sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
              <Chip label="2" color="primary" size="small" />
              <Typography variant="h6" fontWeight={600}>
                Select a Source
              </Typography>
            </Box>
            
            {/* Search & Import */}
            <Stack spacing={2} sx={{ mb: 2 }}>
              <TextField
                fullWidth
                size="small"
                placeholder="Search by name or ID..."
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
                size="small"
                startIcon={<CloudUploadIcon />}
                onClick={() => setOpenSheetDialog(true)}
                fullWidth
              >
                Import from Google Sheets
              </Button>
            </Stack>
            
            {/* Source List */}
            <Box sx={{ flex: 1, overflow: 'auto' }}>
              {loadingHistory ? (
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', py: 4 }}>
                  <CircularProgress size={24} />
                  <Typography variant="body2" sx={{ ml: 2 }}>Loading sources...</Typography>
                </Box>
              ) : filteredHistory.length === 0 ? (
                <Box sx={{ py: 4, textAlign: 'center' }}>
                  <Typography variant="body2" color="text.secondary">
                    {historySearch ? 'No matches found' : 'No source files available'}
                  </Typography>
                </Box>
              ) : (
                <Stack spacing={1}>
                  {filteredHistory.slice(0, 50).map((h) => {
                    const selected = String(h.id) === sourceId;
                    const date = new Date(h.timestamp).toLocaleDateString();
                    const isFromSheets = h.original_filename?.includes('Google Sheets');
                    
                    return (
                      <Card
                        key={h.id}
                        variant="outlined"
                        sx={{
                          border: selected ? 2 : 1,
                          borderColor: selected ? 'primary.main' : 'divider',
                          bgcolor: selected ? 'action.selected' : 'background.paper',
                          transition: 'all 0.2s',
                          '&:hover': {
                            borderColor: 'primary.main',
                            boxShadow: 1,
                          },
                        }}
                      >
                        <CardActionArea onClick={() => setSourceId(String(h.id))}>
                          <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                            <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                              <Box sx={{ color: 'primary.main', mt: 0.5 }}>
                                {isFromSheets ? <SheetsIcon /> : <PdfIcon />}
                              </Box>
                              <Box sx={{ flex: 1, minWidth: 0 }}>
                                <Typography variant="body2" fontWeight={600} noWrap>
                                  {h.original_filename || `Source #${h.id}`}
                                </Typography>
                                <Typography variant="caption" color="text.secondary" display="block">
                                  ID #{h.id} • {h.processed_sentences_count} sentences • {date}
                                </Typography>
                              </Box>
                              <Radio
                                checked={selected}
                                size="small"
                                sx={{ p: 0 }}
                              />
                            </Box>
                          </CardContent>
                        </CardActionArea>
                      </Card>
                    );
                  })}
                </Stack>
              )}
            </Box>
          </Paper>
        </Box>
        
        {/* COLUMN 3: RUN & REVIEW */}
        <Box>
          <Paper sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
            {!currentRunId ? (
              // Initial State: Big Run Button
              <>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
                  <Chip label="3" color="primary" size="small" />
                  <Typography variant="h6" fontWeight={600}>
                    Run Analysis
                  </Typography>
                </Box>
                
                <Box sx={{ 
                  flex: 1, 
                  display: 'flex', 
                  flexDirection: 'column',
                  alignItems: 'center', 
                  justifyContent: 'center',
                  gap: 3,
                }}>
                  <Button
                    variant="contained"
                    size="large"
                    startIcon={<PlayIcon />}
                    onClick={handleRunCoverage}
                    disabled={!sourceId || runMutation.isPending || (creditsData && costData && creditsData.balance < costData.cost)}
                    sx={{
                      py: 3,
                      px: 6,
                      fontSize: '1.1rem',
                      fontWeight: 600,
                      background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
                      boxShadow: '0 3px 5px 2px rgba(33, 203, 243, .3)',
                      '&:hover': {
                        boxShadow: '0 6px 10px 4px rgba(33, 203, 243, .3)',
                      },
                      '&:disabled': {
                        background: 'action.disabledBackground',
                        boxShadow: 'none',
                      },
                    }}
                  >
                    {runMutation.isPending ? 'Starting...' : 'Run Vocabulary Coverage'}
                  </Button>
                  
                  {costData && (
                    <Chip
                      label={`Costs ${costData.cost} Credits`}
                      color="primary"
                      variant="outlined"
                    />
                  )}
                  
                  {creditsData && costData && creditsData.balance < costData.cost && (
                    <Alert severity="warning" sx={{ width: '100%' }}>
                      Insufficient credits. You have {creditsData.balance} credits, but need {costData.cost}.
                    </Alert>
                  )}
                  
                  {!sourceId && (
                    <Typography variant="body2" color="text.secondary" textAlign="center">
                      Please select a source from Column 2 to continue
                    </Typography>
                  )}
                </Box>
              </>
            ) : coverageRun?.status === 'processing' ? (
              // Processing State
              <>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
                  <Chip label="3" color="primary" size="small" />
                  <Typography variant="h6" fontWeight={600}>
                    Processing...
                  </Typography>
                </Box>
                
                <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 3 }}>
                  <Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="body2">Analyzing vocabulary...</Typography>
                      <Typography variant="body2" fontWeight={600}>{coverageRun.progress_percent}%</Typography>
                    </Box>
                    <LinearProgress variant="determinate" value={coverageRun.progress_percent} />
                  </Box>
                  
                  {ws.connected ? (
                    <Chip label="Live Updates" color="success" size="small" icon={<CircularProgress size={12} sx={{ color: 'inherit' }} />} />
                  ) : (
                    <Chip label="Reconnecting..." color="warning" size="small" />
                  )}
                  
                  <Box sx={{ mt: 'auto' }}>
                    <Button
                      variant="outlined"
                      color="error"
                      startIcon={<CancelIcon />}
                      fullWidth
                      disabled
                    >
                      Cancel Run
                    </Button>
                    <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1, textAlign: 'center' }}>
                      Cancellation coming soon
                    </Typography>
                  </Box>
                </Box>
              </>
            ) : coverageRun?.status === 'completed' ? (
              // Results State
              <>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
                  <Chip label="3" color="primary" size="small" />
                  <Typography variant="h6" fontWeight={600}>
                    Results
                  </Typography>
                </Box>
                
                <Stack spacing={3} sx={{ flex: 1, overflow: 'auto' }}>
                  {/* KPI Cards */}
                  <Stack spacing={2}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="caption" color="text.secondary">
                          Sentences Selected
                        </Typography>
                        <Typography variant="h4" fontWeight={600}>
                          {mode === 'coverage' 
                            ? (getNumberStat('selected_sentence_count') ?? learningSetDisplay.length ?? 'N/A')
                            : (getNumberStat('selected_count') ?? 'N/A')}
                        </Typography>
                      </CardContent>
                    </Card>
                    
                    {mode === 'coverage' && (
                      <>
                        <Card variant="outlined">
                          <CardContent>
                            <Typography variant="caption" color="text.secondary">
                              Words Covered
                            </Typography>
                            <Typography variant="h4" fontWeight={600}>
                              {getNumberStat('words_covered') ?? 'N/A'}
                            </Typography>
                          </CardContent>
                        </Card>
                        
                        <Card variant="outlined">
                          <CardContent>
                            <Typography variant="caption" color="text.secondary">
                              Vocabulary Coverage %
                            </Typography>
                            <Typography variant="h4" fontWeight={600}>
                              {(() => {
                                const total = getNumberStat('words_total');
                                const covered = getNumberStat('words_covered');
                                if (total && covered) {
                                  return `${((covered / total) * 100).toFixed(1)}%`;
                                }
                                return 'N/A';
                              })()}
                            </Typography>
                          </CardContent>
                        </Card>
                      </>
                    )}
                    
                    {mode === 'filter' && (
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="caption" color="text.secondary">
                            Acceptance Ratio
                          </Typography>
                          <Typography variant="h4" fontWeight={600}>
                            {((getNumberStat('filter_acceptance_ratio') ?? 0) * 100).toFixed(1)}%
                          </Typography>
                        </CardContent>
                      </Card>
                    )}
                  </Stack>
                  
                  {/* Action Buttons */}
                  <Stack direction="row" spacing={2}>
                    <Button
                      variant="outlined"
                      startIcon={<DownloadIcon />}
                      onClick={handleDownloadCSV}
                      fullWidth
                    >
                      Download CSV
                    </Button>
                    <Button
                      variant="outlined"
                      startIcon={<SheetsIcon />}
                      onClick={() => setShowExportDialog(true)}
                      fullWidth
                    >
                      Export to Sheets
                    </Button>
                  </Stack>
                  
                  {/* Results Preview */}
                  <Box>
                    <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                      Preview Results
                    </Typography>
                    {mode === 'coverage' && learningSetDisplay.length > 0 ? (
                      <LearningSetTable entries={learningSetDisplay.slice(0, 10)} loading={false} />
                    ) : mode === 'filter' && assignments.length > 0 ? (
                      <FilterResultsTable assignments={assignments.slice(0, 10)} loading={false} />
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        No preview available
                      </Typography>
                    )}
                    <Button
                      variant="text"
                      size="small"
                      sx={{ mt: 1 }}
                      onClick={() => {
                        // Scroll down to full results
                        document.getElementById('full-results')?.scrollIntoView({ behavior: 'smooth' });
                      }}
                    >
                      View Full Results Below
                    </Button>
                  </Box>
                  
                  {/* New Analysis Button */}
                  <Button
                    variant="outlined"
                    onClick={() => {
                      setCurrentRunId(null);
                      setSourceId('');
                    }}
                    fullWidth
                  >
                    Start New Analysis
                  </Button>
                </Stack>
              </>
            ) : (
              // Failed/Other States
              <>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
                  <Chip label="3" color="primary" size="small" />
                  <Typography variant="h6" fontWeight={600}>
                    {coverageRun?.status === 'failed' ? 'Failed' : 'Status Unknown'}
                  </Typography>
                </Box>
                
                <Alert severity="error">
                  {coverageRun?.error_message || 'Analysis failed. Please try again.'}
                </Alert>
                
                <Button
                  variant="contained"
                  onClick={() => {
                    setCurrentRunId(null);
                  }}
                  sx={{ mt: 2 }}
                >
                  Try Again
                </Button>
              </>
            )}
          </Paper>
        </Box>
      </Box>
      
      {/* Full Results Section (below the three columns) */}
      {coverageRun?.status === 'completed' && (
        <Box id="full-results" sx={{ mt: 4 }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h5" gutterBottom fontWeight={600}>
              Full Results
            </Typography>
            
            <Divider sx={{ my: 2 }} />
            
            {mode === 'coverage' && learningSetDisplay.length > 0 && (
              <Box>
                <Typography variant="h6" gutterBottom>
                  Learning Set ({learningSetDisplay.length} sentences)
                </Typography>
                <LearningSetTable entries={learningSetDisplay} loading={false} />
              </Box>
            )}
            
            {mode === 'filter' && assignments.length > 0 && (
              <Box>
                <Typography variant="h6" gutterBottom>
                  Filtered Sentences ({assignments.length} results)
                </Typography>
                <FilterResultsTable assignments={assignments} loading={false} />
              </Box>
            )}
          </Paper>
        </Box>
      )}
      
      {/* Help Dialog */}
      <Dialog open={showHelpDialog} onClose={() => setShowHelpDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>About Analysis Modes</DialogTitle>
        <DialogContent>
          <Stack spacing={3} sx={{ mt: 1 }}>
            <Box>
              <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                Coverage Mode
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Finds the minimum number of sentences needed to cover every word in your target list at least once.
                This mode prioritizes comprehensive vocabulary exposure, making it ideal for creating complete learning sets.
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                <strong>Best for:</strong> Ensuring complete vocabulary coverage, comprehensive learning materials
              </Typography>
            </Box>
            
            <Divider />
            
            <Box>
              <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                Filter Mode
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Selects sentences with high vocabulary density (≥95% common words) that are 4-8 words in length.
                Prioritizes shorter, high-quality sentences perfect for daily repetition drills.
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                <strong>Best for:</strong> Daily practice, drilling exercises, beginner-friendly materials
              </Typography>
            </Box>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowHelpDialog(false)} variant="contained">
            Got it
          </Button>
        </DialogActions>
      </Dialog>
      
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
              Finds sentences with at least 4 vocabulary words (nouns, verbs, adjectives, adverbs) from your list
              and 4-8 words in length. Ignores &ldquo;glue words&rdquo; like pronouns, determiners, and conjunctions.
              Perfect for creating high-quality sentences for daily repetition drills.
            </Typography>
          </Box>
          
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

      {/* Import from Sheets Dialog */}
      <Dialog open={openSheetDialog} onClose={() => setOpenSheetDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Import Sentences from Google Sheets</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Google Sheets URL"
            value={sheetUrl}
            onChange={(e) => setSheetUrl(e.target.value)}
            sx={{ mt: 2 }}
            placeholder="https://docs.google.com/spreadsheets/d/..."
            helperText="Paste the full URL or just the spreadsheet ID"
          />
          <Alert severity="info" sx={{ mt: 2 }}>
            <Typography variant="body2" gutterBottom>
              <strong>Sheet Format:</strong>
            </Typography>
            <Typography variant="body2" component="div">
              • Column A: Index (optional, e.g., 1, 2, 3...)
              <br />
              • Column B: Sentence (French sentences)
              <br />
              <br />
              The first row will be detected as a header and skipped if it contains
              &ldquo;Index&rdquo; or &ldquo;Sentence&rdquo;.
            </Typography>
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenSheetDialog(false)}>Cancel</Button>
          <Button 
            variant="contained" 
            onClick={() => importSheetsMutation.mutate(sheetUrl)}
            disabled={!sheetUrl || importSheetsMutation.isPending}
          >
            {importSheetsMutation.isPending ? 'Importing...' : 'Import'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
    </RouteGuard>
  );
}
