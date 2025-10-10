'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Stack,
  Alert,
  Chip,
  CircularProgress,
  TextField,
  InputAdornment,
  Pagination,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Download as DownloadIcon,
  TableChart as SheetsIcon,
  BugReport as DiagnoseIcon,
  Search as SearchIcon,
} from '@mui/icons-material';
import { CoverageRun as CoverageRunType, LearningSetEntry, CoverageAssignment } from '@/lib/types';
import LearningSetTable from '@/components/LearningSetTable';
import FilterResultsTable from '@/components/FilterResultsTable';
import ProcessingState from './ProcessingState';
import ResultsKPICards from './ResultsKPICards';
import BatchModeSummary from './BatchModeSummary';
import UncoveredWordsCard from './UncoveredWordsCard';

interface RunReviewStepProps {
  currentRunId: number | null;
  coverageRun: CoverageRunType | undefined;
  loadingRun: boolean;
  learningSetDisplay: LearningSetEntry[];
  assignments: CoverageAssignment[];
  mode: 'coverage' | 'filter';
  isBatchMode: boolean;
  selectedSourceIds: number[];
  sourceId: string;
  creditsData: { balance: number } | undefined;
  costData: { cost: number } | undefined;
  onRunCoverage: () => void;
  runMutationPending: boolean;
  onDownloadCSV: () => void;
  onShowExportDialog: () => void;
  onDiagnose: () => void;
  onStartNewAnalysis: () => void;
}

const RESULTS_PAGE_SIZE = 10;

export default function RunReviewStep({
  currentRunId,
  coverageRun,
  loadingRun,
  learningSetDisplay,
  assignments,
  mode,
  isBatchMode,
  selectedSourceIds,
  sourceId,
  creditsData,
  costData,
  onRunCoverage,
  runMutationPending,
  onDownloadCSV,
  onShowExportDialog,
  onDiagnose,
  onStartNewAnalysis,
}: RunReviewStepProps) {
  const [resultsPage, setResultsPage] = useState<number>(1);
  const [resultsSearch, setResultsSearch] = useState('');

  // Reset preview pagination whenever a new run is loaded
  useEffect(() => {
    setResultsPage(1);
  }, [currentRunId, coverageRun?.id]);

  // Helper to safely read numeric stats from unknown stats_json
  const getNumberStat = (key: string): number | null => {
    const stats = coverageRun?.stats_json as Record<string, unknown> | undefined;
    if (!stats) return null;
    const v = stats[key];
    if (typeof v === 'number') return v;
    if (typeof v === 'string' && v.trim() !== '' && !Number.isNaN(Number(v))) return Number(v);
    return null;
  };

  if (!currentRunId) {
    // Initial State: Big Run Button
    return (
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
              onClick={onRunCoverage}
              disabled={
                runMutationPending ||
                (isBatchMode ? selectedSourceIds.length < 2 : !sourceId) ||
                (creditsData && costData && creditsData.balance < costData.cost)
              }
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
              {runMutationPending
                ? 'Starting...'
                : isBatchMode
                  ? `Run Batch Analysis`
                  : 'Start'}
            </Button>

            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 2 }}>
              {isBatchMode
                ? `Batch mode will process ${selectedSourceIds.length} sources sequentially for maximum coverage.`
                : 'This will start the analysis and may take a few minutes.'}
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
    );
  }

  if (loadingRun && currentRunId && !coverageRun) {
    // Run exists but is still being fetched from the server
    return (
      <>
        <Typography variant="h5" fontWeight={600} gutterBottom>
          Loading Run...
        </Typography>

        <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 2 }}>
          <CircularProgress />
          <Typography variant="body1">Fetching run results...</Typography>
        </Box>
      </>
    );
  }

  if (coverageRun?.status === 'processing') {
    return <ProcessingState progressPercent={coverageRun.progress_percent} />;
  }

  if (coverageRun?.status === 'completed') {
    const total = getNumberStat('words_total');
    const covered = getNumberStat('words_covered');
    const uncovered = total && covered ? total - covered : 0;

    return (
      <>
        <Typography variant="h5" fontWeight={600} gutterBottom>
          Results
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
          Your vocabulary coverage analysis is complete
        </Typography>

        <Stack spacing={3}>
          {/* Enhanced KPI Cards */}
          <ResultsKPICards
            mode={coverageRun.mode as 'coverage' | 'filter' | 'batch'}
            selectedCount={
              coverageRun.mode === 'filter'
                ? assignments.length
                : (getNumberStat('selected_count') ?? getNumberStat('selected_sentence_count'))
            }
            wordsCovered={covered}
            wordsTotal={total}
            filterAcceptanceRatio={getNumberStat('filter_acceptance_ratio')}
            learningSetDisplayLength={learningSetDisplay.length}
          />

          {/* Batch Mode Summary */}
          {coverageRun.mode === 'batch' && coverageRun.stats_json && (
            <BatchModeSummary statsJson={coverageRun.stats_json as Record<string, unknown>} />
          )}

          {/* Uncovered Words Quick Summary (Coverage Mode Only) */}
          {coverageRun.mode !== 'filter' && (
            <UncoveredWordsCard uncoveredCount={uncovered} onDiagnose={onDiagnose} loading={loadingRun} />
          )}

          {/* Action Buttons */}
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
            <Button
              variant="outlined"
              startIcon={<DownloadIcon />}
              onClick={onDownloadCSV}
              fullWidth
              disabled={loadingRun}
            >
              Download CSV
            </Button>
            <Button
              variant="outlined"
              startIcon={<SheetsIcon />}
              onClick={onShowExportDialog}
              fullWidth
              disabled={loadingRun}
            >
              Export to Sheets
            </Button>
            {coverageRun.mode !== 'filter' && (
              <Button
                variant="outlined"
                startIcon={<DiagnoseIcon />}
                onClick={onDiagnose}
                fullWidth
                disabled={loadingRun}
              >
                Diagnose Coverage
              </Button>
            )}
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
                    slotProps={{
                      input: {
                        startAdornment: (
                          <InputAdornment position="start">
                            <SearchIcon fontSize="small" />
                          </InputAdornment>
                        ),
                      },
                    }}
                  />
                </Box>

                <LearningSetTable
                  entries={learningSetDisplay}
                  loading={loadingRun}
                  disablePagination
                  externalSearchQuery={resultsSearch}
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
            ) : coverageRun.mode === 'filter' && assignments.length > 0 ? (
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
            onClick={onStartNewAnalysis}
            fullWidth
          >
            Start New Analysis
          </Button>
        </Stack>
      </>
    );
  }

  // Failed / Pending / Other States
  return (
    <>
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
        onClick={onStartNewAnalysis}
      >
        Start Over
      </Button>
    </>
  );
}
