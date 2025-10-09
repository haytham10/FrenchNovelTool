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
  Alert,
  CircularProgress,
  LinearProgress,
  Chip,
  Stack,
  Divider,
  Pagination,
  SelectChangeEvent,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  InputAdornment,
  Slider,
  Card,
  CardContent,
  CardActionArea,
  IconButton,
  Tooltip,
  Radio,
  Stepper,
  Step,
  StepLabel,
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
  ArrowBack as ArrowBackIcon,
  ArrowForward as ArrowForwardIcon,
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

const WIZARD_STEPS = ['Configure', 'Select Source', 'Run & Review'] as const;

export default function CoveragePage() {
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const { enqueueSnackbar } = useSnackbar();
  
  // Get URL parameters for pre-filling
  const urlSource = searchParams.get('source'); // 'job' or 'history'
  const urlId = searchParams.get('id');
  const urlRunId = searchParams.get('runId'); // Pre-existing run to view
  
  // State
  const [mode, setMode] = useState<'coverage' | 'filter'>('coverage');
  // Source is now only from history (UI removed for Job ID)
  const [sourceId, setSourceId] = useState<string>(urlId || '');
  const [selectedWordListId, setSelectedWordListId] = useState<number | ''>('');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [currentRunId, setCurrentRunId] = useState<number | null>(urlRunId ? parseInt(urlRunId) : null);
  const [historySearch, setHistorySearch] = useState<string>('');
  // Pagination for history list (step 2)
  const [historyPage, setHistoryPage] = useState<number>(1);
  const HISTORY_PAGE_SIZE = 5;
  const [openSheetDialog, setOpenSheetDialog] = useState<boolean>(false);
  const [sheetUrl, setSheetUrl] = useState<string>('');
  // const [resultSearch, setResultSearch] = useState<string>('');
  const [showExportDialog, setShowExportDialog] = useState<boolean>(false);
  const [exportSheetName, setExportSheetName] = useState<string>('');
  const [sentenceCap, setSentenceCap] = useState<number>(500); // Coverage mode sentence cap (0 = unlimited)
  // Load user settings to know which default wordlist is configured
  const { data: settings } = useSettings();
  
  // Wizard step state
  const [activeStep, setActiveStep] = useState<number>(currentRunId ? 2 : 0);
  
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
  
    // Call the hook for side effects only (don't assign to an unused variable)
    useCoverageWebSocket({
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
  // Pagination for previewed results (show 10 per page)
  const [resultsPage, setResultsPage] = useState<number>(1);
  const RESULTS_PAGE_SIZE = 10;
  const [resultsSearch, setResultsSearch] = React.useState('');

  // Reset preview pagination whenever a new run is loaded
  useEffect(() => {
    setResultsPage(1);
  }, [currentRunId, coverageRun?.id]);
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

  // Reset pagination when search changes
  useEffect(() => {
    setHistoryPage(1);
  }, [historySearch]);

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
  
  // Wizard navigation handlers
  const handleStepBack = () => {
    setActiveStep((prev) => Math.max(prev - 1, 0));
  };
  
  const handleStepNext = () => {
    setActiveStep((prev) => Math.min(prev + 1, WIZARD_STEPS.length - 1));
  };
  
  // Validation for next button
  const isNextDisabled = React.useMemo(() => {
    if (activeStep === 0) return false; // Configure step always allows next
    if (activeStep === 1) return !sourceId; // Select Source requires a source
    return true; // Run & Review is the final step
  }, [activeStep, sourceId]);
  
  const nextButtonLabel = activeStep === WIZARD_STEPS.length - 1 ? 'Finish' : 'Next';
  
  // Update active step when a run is started
  useEffect(() => {
    if (currentRunId && activeStep < 2) {
      setActiveStep(2);
    }
  }, [currentRunId, activeStep]);
  
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
        
      {/* Wizard Stepper */}
	<Paper sx={{ mb: 2 }}>
		<Stepper activeStep={activeStep} sx={{ p: 2 }} alternativeLabel>
			{WIZARD_STEPS.map((label) => (
				<Step key={label}>
					<StepLabel>{label}</StepLabel>
				</Step>
			))}
		</Stepper>
	</Paper>
      
      {/* Step Content */}
      <Paper sx={{ p: 4, height: '100%', display: 'flex', flexDirection: 'column' }}>
        {activeStep === 0 && (
          // STEP 1: CONFIGURE
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
                      <IconButton size="small" onClick={() => setShowHelpDialog(true)}>
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
                        disabled={uploadMutation.isPending}
                        size="small"
                      >
                        {uploadMutation.isPending ? 'Confirming...' : 'Confirm Upload'}
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
							step={1} // allow any integer value in the range
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
									// empty means unlimited
									setSentenceCap(0);
									return;
								}
								const val = Number(raw);
								if (!Number.isFinite(val)) return;
								// interpret 1000 as unlimited (∞), otherwise clamp to allowed range
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
        )}
        
        {activeStep === 1 && (
          // STEP 2: SELECT SOURCE
          <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Typography variant="h5" fontWeight={600} gutterBottom>
              Select a Source
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
              Choose a previously processed document or import from Google Sheets
            </Typography>
            
            {/* Search & Import */}
            <Stack direction="row" spacing={2} sx={{ mb: 3 }}>
              <TextField
                fullWidth
                placeholder="Search by name or ID..."
                value={historySearch}
                onChange={(e) => setHistorySearch(e.target.value)}
                slotProps={{
                  input: {
                    startAdornment: (
                      <InputAdornment position="start">
                        <SearchIcon />
                      </InputAdornment>
                    ),
                  },
                }}
              />
              <Button
                variant="outlined"
                startIcon={<CloudUploadIcon />}
                onClick={() => setOpenSheetDialog(true)}
                sx={{ flexShrink: 0 }}
              >
                Import from Sheets
              </Button>
            </Stack>
            
            {/* Source List */}
            <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'auto', border: 1, borderColor: 'divider', borderRadius: 1, p: 2 }}>
              {loadingHistory ? (
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', py: 8 }}>
                  <CircularProgress size={32} />
                  <Typography variant="body1" sx={{ ml: 2 }}>Loading sources...</Typography>
                </Box>
              ) : filteredHistory.length === 0 ? (
                <Box sx={{ py: 8, textAlign: 'center' }}>
                  <Typography variant="body1" color="text.secondary">
                    {historySearch ? 'No matches found' : 'No source files available'}
                  </Typography>
                </Box>
              ) : (
                <>
                <Stack spacing={2}>
                  {filteredHistory.slice((historyPage - 1) * HISTORY_PAGE_SIZE, historyPage * HISTORY_PAGE_SIZE).map((h) => {
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
                                <Typography variant="body1" fontWeight={600} noWrap>
                                  {h.original_filename || `Source #${h.id}`}
                                </Typography>
                                <Typography variant="body2" color="text.secondary" display="block">
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

                {/* Pagination controls */}
                {filteredHistory.length > HISTORY_PAGE_SIZE && (
                  <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
                    <Pagination
                      count={Math.ceil(filteredHistory.length / HISTORY_PAGE_SIZE)}
                      page={historyPage}
                      onChange={(_, p) => setHistoryPage(p)}
                      color="primary"
                    />
                  </Box>
                )}
                </>
              )}
            </Box>
          </Box>
        )}
        
        {activeStep === 2 && (
          // STEP 3: RUN & REVIEW
          <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            {!currentRunId ? (
              // Initial State: Big Run Button
              <>
                <Typography variant="h5" fontWeight={600} gutterBottom>
                  Run Analysis
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
                  Start the vocabulary coverage analysis
                </Typography>
                
                <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Box sx={{ width: '100%', maxWidth: 640, textAlign: 'center' }}>
                    <Button
                      variant="contained"
                      onClick={handleRunCoverage}
                      disabled={!sourceId || runMutation.isPending || (creditsData && costData && creditsData.balance < costData.cost)}
                      startIcon={<PlayIcon sx={{ ml: -0.5 }} />}
                      sx={{
                        width: { xs: '100%', sm: '60%', md: '45%' },
                        py: 2.25,
                        px: 4,
                        fontSize: '1.05rem',
                        fontWeight: 700,
                        borderRadius: 2,
                        textTransform: 'none',
                        background: 'linear-gradient(90deg, #2196F3 0%, #21CBF3 100%)',
                        boxShadow: '0 8px 24px rgba(33,203,243,0.14)',
                        '&:hover': {
                          boxShadow: '0 12px 30px rgba(33,203,243,0.18)',
                        },
                        '&:disabled': {
                          background: 'action.disabledBackground',
                          boxShadow: 'none',
                        },
                      }}
                    >
                      {runMutation.isPending ? 'Starting...' : 'Start'}
                    </Button>

                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 2 }}>
                      This will start the analysis and may take a few minutes.
                    </Typography>

                    <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center', gap: 1, alignItems: 'center', flexDirection: { xs: 'column', sm: 'row' } }}>
                      {costData && (
                        <Chip label={`Costs ${costData.cost} Credits`} color="primary" variant="outlined" />
                      )}

                      {creditsData && costData && creditsData.balance < costData.cost && (
                        <Alert severity="warning" sx={{ maxWidth: 520 }}>
                          Insufficient credits. You have {creditsData.balance} credits, but need {costData.cost}.
                        </Alert>
                      )}
                    </Box>

                    {!sourceId && (
                      <Typography variant="body2" color="text.secondary" textAlign="center" sx={{ mt: 2 }}>
                        Please select a source from the previous step
                      </Typography>
                    )}
                  </Box>
                </Box>
              </>
            ) : (loadingRun && currentRunId && !coverageRun) ? (
              // Run exists but is still being fetched from the server
              <>
                <Typography variant="h5" fontWeight={600} gutterBottom>
                  Loading Run...
                </Typography>

                <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 2 }}>
                  <CircularProgress />
                  <Typography variant="body1">Fetching run results...</Typography>
                </Box>
              </>
            ) : coverageRun?.status === 'processing' ? (
              // Processing State
              <>
                <Typography variant="h5" fontWeight={600} gutterBottom>
                  Processing...
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
                  Your vocabulary coverage analysis is in progress
                </Typography>
                
                <Box sx={{ maxWidth: 600, mx: 'auto', width: '100%' }}>
                  <Box sx={{ mb: 4 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="body1">Analyzing vocabulary...</Typography>
                      <Typography variant="body1" fontWeight={600}>{coverageRun.progress_percent}%</Typography>
                    </Box>
                    <LinearProgress variant="determinate" value={coverageRun.progress_percent} sx={{ height: 8, borderRadius: 1 }} />
                  </Box>
                  <Box sx={{ mt: 4 }}>
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
                <Typography variant="h5" fontWeight={600} gutterBottom>
                  Results
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
                  Your vocabulary coverage analysis is complete
                </Typography>
                
                <Stack spacing={3}>
                  {/* KPI Cards */}
                  <Stack direction="row" spacing={2}>
                    <Card variant="outlined" sx={{ flex: 1 }}>
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
                        <Card variant="outlined" sx={{ flex: 1 }}>
                          <CardContent>
                            <Typography variant="caption" color="text.secondary">
                              Words Covered
                            </Typography>
                            <Typography variant="h4" fontWeight={600}>
                              {getNumberStat('words_covered') ?? 'N/A'}
                            </Typography>
                          </CardContent>
                        </Card>
                        
                        <Card variant="outlined" sx={{ flex: 1 }}>
                          <CardContent>
                            <Typography variant="caption" color="text.secondary">
                              Coverage %
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
                      <Card variant="outlined" sx={{ flex: 1 }}>
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
                      disabled={loadingRun}
                    >
                      Download CSV
                    </Button>
                    <Button
                      variant="outlined"
                      startIcon={<SheetsIcon />}
                      onClick={() => setShowExportDialog(true)}
                      fullWidth
                      disabled={loadingRun}
                    >
                      Export to Sheets
                    </Button>
                  </Stack>
                  
                <Box>
                    {mode === 'coverage' && learningSetDisplay.length > 0 ? (
						<>
						  {/* Page-level search that applies to the whole result set */}
						  <Box sx={{ mb: 2 }}>
							<TextField
							  fullWidth
							  size="small"
							  placeholder="Search by rank or sentence..."
							  value={resultsSearch}
							  onChange={(e) => { setResultsSearch(e.target.value); setResultsPage(1); }}
							  InputProps={{
								startAdornment: (
								  <InputAdornment position="start">
									<SearchIcon fontSize="small" />
								  </InputAdornment>
								),
							  }}
							/>
						  </Box>

						  <LearningSetTable
							// pass full entries and let the table know an externalSearchQuery is active
							entries={learningSetDisplay}
							loading={loadingRun}
							disablePagination
							externalSearchQuery={resultsSearch}
							// we still slice at the page-level for visible rows
							pageSliceStart={(resultsPage - 1) * RESULTS_PAGE_SIZE}
							pageSliceEnd={resultsPage * RESULTS_PAGE_SIZE}
						  />
					  {learningSetDisplay.length > RESULTS_PAGE_SIZE && (
						<Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
						  <Pagination
							count={Math.ceil(learningSetDisplay.length / RESULTS_PAGE_SIZE)}
							page={resultsPage}
							onChange={(_, p) => setResultsPage(p)}
							color="primary"
						  />
						</Box>
					  )}
						</>
                    ) : mode === 'filter' && assignments.length > 0 ? (
                      <FilterResultsTable
                        assignments={assignments}
                        loading={loadingRun}
                      />
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        No results
                      </Typography>
                    )}
                  </Box>
                  
                  {/* New Analysis Button */}
                  <Button
                    variant="outlined"
                    onClick={() => {
                      setCurrentRunId(null);
                      setSourceId('');
                      setActiveStep(0);
                    }}
                    fullWidth
                  >
                    Start New Analysis
                  </Button>
                </Stack>
              </>
            ) : (
              // Failed / Pending / Other States
              <>
                {/* Render a clearer message for pending (starting) state so users don't
                    briefly see an error-looking UI while the background worker picks up
                    the job. Keep failed/unknown behavior unchanged. */}
                <Typography
                  variant="h5"
                  fontWeight={600}
                  gutterBottom
                  color={coverageRun?.status === 'failed' ? 'error' : 'text.primary'}
                >
                  {coverageRun?.status === 'failed'
                    ? 'Analysis Failed'
                    : coverageRun?.status === 'pending'
                    ? 'Starting Analysis'
                    : 'Status Unknown'}
                </Typography>

                <Alert
                  severity={coverageRun?.status === 'failed' ? 'error' : coverageRun?.status === 'pending' ? 'info' : 'error'}
                  sx={{ mb: 3 }}
                >
                  {coverageRun?.status === 'failed'
                    ? (coverageRun?.error_message || 'Analysis failed. Please try again.')
                    : coverageRun?.status === 'pending'
                    ? 'Your analysis has been queued and will start shortly. This message will update when processing begins.'
                    : (coverageRun?.error_message || 'Analysis failed. Please try again.')}
                </Alert>

                <Button
                  variant="contained"
                  onClick={() => {
                    setCurrentRunId(null);
                    setActiveStep(0);
                  }}
                >
                  Start Over
                </Button>
              </>
            )}
          </Box>
        )}
      	</Paper>
      
      {/* Navigation Buttons */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 3 }}>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={handleStepBack}
          disabled={activeStep === 0}
          size="large"
        >
          Back
        </Button>
        {
          // Hide the Finish (Next) button when the run is actively processing
          // and the user is on the final step. This prevents accidental
          // navigation while a processing run is in progress.
          !(activeStep === WIZARD_STEPS.length - 1 && coverageRun?.status === 'processing') && (
            <Button
              endIcon={<ArrowForwardIcon />}
              onClick={handleStepNext}
              disabled={isNextDisabled}
              variant="contained"
              size="large"
            >
              {nextButtonLabel}
            </Button>
          )
        }
      </Box>
      
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
              Coverage Mode (Comprehensive Learning)
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Selects a minimal set of sentences that covers all vocabulary words in your list, 
              prioritizing shorter sentences with more content words. Focuses on nouns, verbs, adjectives,
              and adverbs while ignoring function words. Useful for ensuring complete vocabulary exposure.
            </Typography>

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
