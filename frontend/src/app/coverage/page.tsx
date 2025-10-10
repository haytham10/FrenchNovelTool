'use client';

import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Container,
  Typography,
  Paper,
  Button,
  Stepper,
  Step,
  StepLabel,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  ArrowForward as ArrowForwardIcon,
} from '@mui/icons-material';
import { useSearchParams } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { useSettingsStore } from '@/stores/useSettingsStore';
import {
  CoverageRun as CoverageRunType,
  CoverageAssignment,
  LearningSetEntry,
  HistoryEntry,
  CoverageDiagnosis,
} from '@/lib/types';
import { useCoverageWebSocket } from '@/lib/useCoverageWebSocket';
import RouteGuard from '@/components/RouteGuard';
import Breadcrumbs from '@/components/Breadcrumbs';

// Coverage-specific components
import ConfigureStep from '@/components/coverage/ConfigureStep';
import SelectSourceStep from '@/components/coverage/SelectSourceStep';
import RunReviewStep from '@/components/coverage/RunReviewStep';
import HelpDialog from '@/components/coverage/HelpDialog';
import ExportDialog from '@/components/coverage/ExportDialog';
import ImportDialog from '@/components/coverage/ImportDialog';
import DiagnosisDialog from '@/components/coverage/DiagnosisDialog';
import InfoPanel from '@/components/coverage/InfoPanel';

// Custom hooks
import { useCoverageData } from '@/hooks/useCoverageData';
import { useCoverageMutations } from '@/hooks/useCoverageMutations';

const WIZARD_STEPS = ['Configure', 'Select Source', 'Run & Review'] as const;
const HISTORY_PAGE_SIZE = 5;

export default function CoveragePage() {
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const settings = useSettingsStore((state) => state.settings);

  // Get URL parameters for pre-filling
  const urlId = searchParams.get('id');
  const urlRunId = searchParams.get('runId');

  // State
  const [mode, setMode] = useState<'coverage' | 'filter'>('coverage');
  const [sourceId, setSourceId] = useState<string>(urlId || '');
  const [selectedSourceIds, setSelectedSourceIds] = useState<number[]>([]);
  const [isBatchMode, setIsBatchMode] = useState<boolean>(false);
  const [selectedWordListId, setSelectedWordListId] = useState<number | ''>('');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [currentRunId, setCurrentRunId] = useState<number | null>(
    urlRunId ? parseInt(urlRunId) : null
  );
  const [historySearch, setHistorySearch] = useState<string>('');
  const [historyPage, setHistoryPage] = useState<number>(1);
  const [openSheetDialog, setOpenSheetDialog] = useState<boolean>(false);
  const [sheetUrl, setSheetUrl] = useState<string>('');
  const [showExportDialog, setShowExportDialog] = useState<boolean>(false);
  const [exportSheetName, setExportSheetName] = useState<string>('');
  const [showDiagnosisDialog, setShowDiagnosisDialog] = useState<boolean>(false);
  const [diagnosisData, setDiagnosisData] = useState<CoverageDiagnosis | null>(null);
  const [loadingDiagnosis, setLoadingDiagnosis] = useState<boolean>(false);
  const [sentenceCap, setSentenceCap] = useState<number>(500);
  const [activeStep, setActiveStep] = useState<number>(currentRunId ? 2 : 0);
  const [showHelpDialog, setShowHelpDialog] = useState(false);

  // Load data
  const {
    wordListsData,
    loadingWordLists,
    costData,
    creditsData,
    runData,
    loadingRun,
    historyData,
    loadingHistory,
  } = useCoverageData(currentRunId);

  // Setup mutations
  const {
    uploadMutation,
    importSheetsMutation,
    runMutation,
    exportMutation,
    handleDownloadCSV,
    handleDiagnose,
  } = useCoverageMutations({
    setSelectedWordListId,
    setUploadedFile,
    setSourceId,
    setOpenSheetDialog,
    setSheetUrl,
    setCurrentRunId,
    setShowExportDialog,
    setDiagnosisData,
    setShowDiagnosisDialog,
    setLoadingDiagnosis,
  });

  // Real-time updates via WebSocket
  type CoverageRunQueryData = {
    coverage_run: CoverageRunType;
    assignments?: CoverageAssignment[];
    pagination?: { page: number; per_page: number; total: number; pages: number };
    learning_set?: LearningSetEntry[];
  };

  useCoverageWebSocket({
    runId: currentRunId ?? null,
    enabled: !!currentRunId,
    onProgress: (run) => {
      queryClient.setQueryData<CoverageRunQueryData | undefined>(
        ['coverageRun', run.id],
        (old) => {
          if (old) return { ...old, coverage_run: { ...old.coverage_run, ...run } };
          return {
            coverage_run: {
              ...run,
              learning_set_json: run.learning_set_json ?? null,
              started_at: run.started_at ?? null,
            },
            assignments: [],
            learning_set: [],
          };
        }
      );
    },
    onComplete: (run) => {
      queryClient.invalidateQueries({ queryKey: ['coverageRun', run.id] });
    },
  });

  // Derived data
  const wordlists = wordListsData?.wordlists || [];
  const coverageRun = runData?.coverage_run ? {
    ...runData.coverage_run,
    learning_set_json: runData.coverage_run.learning_set_json ?? null,
  } : undefined;
  const assignments = useMemo(
    () =>
      (runData?.assignments?.filter((a) => a.run_id !== undefined) as CoverageAssignment[]) ?? [],
    [runData?.assignments]
  );
  const learningSet = useMemo(
    () => ((runData?.learning_set as LearningSetEntry[] | undefined) ?? []),
    [runData?.learning_set]
  );

  const learningSetDisplay = useMemo(() => {
    if (!learningSet || learningSet.length === 0) return [];

    if (coverageRun?.mode === 'batch') {
      return learningSet as LearningSetEntry[];
    }

    // Single-mode logic
    const sentenceMap = new Map<number, LearningSetEntry & { words: string[] }>();
    for (const item of learningSet) {
      if (item.sentence_index !== null) {
        sentenceMap.set(item.sentence_index, { ...item, words: [] });
      }
    }

    for (const assignment of assignments) {
      if (assignment.sentence_index !== null) {
        const entry = sentenceMap.get(assignment.sentence_index);
        if (entry) {
          const surfaceForm =
            assignment.surface_form || assignment.word_key;
          entry.words.push(surfaceForm);
        }
      }
    }

    return Array.from(sentenceMap.values()).sort(
      (a, b) => (a.sentence_index ?? 0) - (b.sentence_index ?? 0)
    );
  }, [learningSet, assignments, coverageRun?.mode]);

  // Process history
  const history = (historyData || [])
    .slice()
    .sort(
      (a: HistoryEntry, b: HistoryEntry) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );

  const filteredHistory = history.filter((h: HistoryEntry) => {
    if (!historySearch) return true;
    const q = historySearch.toLowerCase().trim();
    return (
      h.original_filename?.toLowerCase().includes(q) ||
      String(h.id).includes(q) ||
      (h.job_id ? String(h.job_id).includes(q) : false)
    );
  });

  // Determine default wordlist
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

  // Reset pagination when search changes
  useEffect(() => {
    setHistoryPage(1);
  }, [historySearch]);

  // Update active step when a run is started
  useEffect(() => {
    if (currentRunId && activeStep < 2) {
      setActiveStep(2);
    }
  }, [currentRunId, activeStep]);

  // Event handlers
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
    const config =
      mode === 'filter'
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
            target_count: sentenceCap,
          };

    if (isBatchMode && selectedSourceIds.length >= 2) {
      runMutation.mutate({
        mode: 'batch',
        sourceType: 'history',
        sourceIds: selectedSourceIds,
        wordlistId: selectedWordListId || undefined,
        config,
      });
    } else {
      runMutation.mutate({
        mode,
        sourceType: 'history',
        sourceId: parseInt(sourceId),
        wordlistId: selectedWordListId || undefined,
        config,
      });
    }
  };

  const handleToggleSourceSelection = (historyId: number) => {
    if (isBatchMode) {
      setSelectedSourceIds((prev) => {
        if (prev.includes(historyId)) {
          return prev.filter((id) => id !== historyId);
        } else {
          return [...prev, historyId];
        }
      });
    } else {
      setSourceId(String(historyId));
    }
  };

  const handleBatchModeToggle = (newBatchMode: boolean) => {
    setIsBatchMode(newBatchMode);
    if (newBatchMode) {
      setSourceId('');
      setSelectedSourceIds([]);
    } else {
      setSelectedSourceIds([]);
      setSourceId('');
    }
  };

  const handleStepBack = () => {
    setActiveStep((prev) => Math.max(prev - 1, 0));
  };

  const handleStepNext = () => {
    setActiveStep((prev) => Math.min(prev + 1, WIZARD_STEPS.length - 1));
  };

  const isNextDisabled = useMemo(() => {
    if (activeStep === 0) return false;
    if (activeStep === 1) {
      if (isBatchMode) {
        return selectedSourceIds.length < 2;
      } else {
        return !sourceId;
      }
    }
    return true;
  }, [activeStep, sourceId, selectedSourceIds, isBatchMode]);

  const nextButtonLabel = activeStep === WIZARD_STEPS.length - 1 ? 'Finish' : 'Next';

  return (
    <RouteGuard>
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Breadcrumbs
          items={[{ label: 'Home', href: '/' }, { label: 'Vocabulary Coverage' }]}
        />

        <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Typography variant="h3" component="h1" gutterBottom sx={{ mb: 1 }}>
              Vocabulary Coverage Tool
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Analyze sentences based on high-frequency vocabulary. Perfect for creating
              optimized language learning materials.
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
            <ConfigureStep
              mode={mode}
              setMode={setMode}
              selectedWordListId={selectedWordListId}
              setSelectedWordListId={setSelectedWordListId}
              sentenceCap={sentenceCap}
              setSentenceCap={setSentenceCap}
              wordlists={wordlists}
              loadingWordLists={loadingWordLists}
              resolvedDefaultWordlist={resolvedDefaultWordlist}
              uploadedFile={uploadedFile}
              handleFileUpload={handleFileUpload}
              handleUploadWordList={handleUploadWordList}
              uploadMutationPending={uploadMutation.isPending}
              onShowHelp={() => setShowHelpDialog(true)}
            />
          )}

          {activeStep === 1 && (
            <SelectSourceStep
              isBatchMode={isBatchMode}
              setIsBatchMode={handleBatchModeToggle}
              selectedSourceIds={selectedSourceIds}
              sourceId={sourceId}
              historySearch={historySearch}
              setHistorySearch={setHistorySearch}
              filteredHistory={filteredHistory}
              loadingHistory={loadingHistory}
              historyPage={historyPage}
              setHistoryPage={setHistoryPage}
              historyPageSize={HISTORY_PAGE_SIZE}
              onToggleSourceSelection={handleToggleSourceSelection}
              onOpenImportDialog={() => setOpenSheetDialog(true)}
            />
          )}

          {activeStep === 2 && (
            <RunReviewStep
              currentRunId={currentRunId}
              coverageRun={coverageRun}
              loadingRun={loadingRun}
              learningSetDisplay={learningSetDisplay}
              assignments={assignments}
              mode={mode}
              isBatchMode={isBatchMode}
              selectedSourceIds={selectedSourceIds}
              sourceId={sourceId}
              creditsData={creditsData}
              costData={costData}
              onRunCoverage={handleRunCoverage}
              runMutationPending={runMutation.isPending}
              onDownloadCSV={() => currentRunId && handleDownloadCSV(currentRunId)}
              onShowExportDialog={() => setShowExportDialog(true)}
              onDiagnose={() => currentRunId && handleDiagnose(currentRunId)}
              onStartNewAnalysis={() => {
                setCurrentRunId(null);
                setSourceId('');
                setActiveStep(0);
              }}
            />
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
          {!(activeStep === WIZARD_STEPS.length - 1 && coverageRun?.status === 'processing') && (
            <Button
              endIcon={<ArrowForwardIcon />}
              onClick={handleStepNext}
              disabled={isNextDisabled}
              variant="contained"
              size="large"
            >
              {nextButtonLabel}
            </Button>
          )}
        </Box>

        {/* Info Panel */}
        <InfoPanel />

        {/* Dialogs */}
        <HelpDialog open={showHelpDialog} onClose={() => setShowHelpDialog(false)} />

        <ExportDialog
          open={showExportDialog}
          onClose={() => setShowExportDialog(false)}
          sheetName={exportSheetName}
          setSheetName={setExportSheetName}
          onExport={() =>
            currentRunId &&
            exportMutation.mutate({ runId: currentRunId, sheetName: exportSheetName })
          }
          exporting={exportMutation.isPending}
        />

        <ImportDialog
          open={openSheetDialog}
          onClose={() => setOpenSheetDialog(false)}
          sheetUrl={sheetUrl}
          setSheetUrl={setSheetUrl}
          onImport={() => importSheetsMutation.mutate(sheetUrl)}
          importing={importSheetsMutation.isPending}
        />

        <DiagnosisDialog
          open={showDiagnosisDialog}
          onClose={() => setShowDiagnosisDialog(false)}
          loading={loadingDiagnosis}
          diagnosisData={diagnosisData}
        />
      </Container>
    </RouteGuard>
  );
}
