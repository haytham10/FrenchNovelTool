'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';
import { AxiosError } from 'axios';
import {
  createWordListFromFile,
  importSentencesFromSheets,
  createCoverageRun,
  exportCoverageRun,
  downloadCoverageRunCSV,
  diagnoseCoverageRun,
} from '@/lib/api';
import type { CoverageDiagnosis } from '@/lib/types';

interface UseCoverageMutationsProps {
  setSelectedWordListId: (id: number) => void;
  setUploadedFile: (file: File | null) => void;
  setSourceId: (id: string) => void;
  setOpenSheetDialog: (open: boolean) => void;
  setSheetUrl: (url: string) => void;
  setCurrentRunId: (id: number | null) => void;
  setShowExportDialog: (open: boolean) => void;
  setDiagnosisData: (data: CoverageDiagnosis | null) => void;
  setShowDiagnosisDialog: (open: boolean) => void;
  setLoadingDiagnosis: (loading: boolean) => void;
}

export function useCoverageMutations({
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
}: UseCoverageMutationsProps) {
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();

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
      queryClient.invalidateQueries({ queryKey: ['history'] });
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
    mutationFn: async (params: {
      mode: 'coverage' | 'filter' | 'batch';
      sourceType: 'history';
      sourceId?: number;
      sourceIds?: number[];
      wordlistId?: number;
      config: Record<string, unknown>;
    }) => {
      return createCoverageRun({
        mode: params.mode,
        source_type: params.sourceType,
        source_id: params.sourceId,
        source_ids: params.sourceIds,
        wordlist_id: params.wordlistId,
        config: params.config,
      });
    },
    onSuccess: (data, variables) => {
      setCurrentRunId(data.coverage_run.id);
      queryClient.invalidateQueries({ queryKey: ['credits'] });
      const modeDisplay = variables.mode === 'batch'
        ? `Batch (${variables.sourceIds?.length} sources)`
        : variables.mode;
      enqueueSnackbar(
        `Coverage run started (${modeDisplay})! ${data.credits_charged} credits charged.`,
        { variant: 'success' }
      );
    },
    onError: (error: unknown) => {
      let msg = 'Failed to start coverage run';
      if (error instanceof AxiosError) {
        const data = error.response?.data;
        if (data && typeof data === 'object' && 'error' in data && typeof data.error === 'string') {
          msg = data.error;
        } else if (error.message) {
          msg = error.message;
        }
      } else if (error instanceof Error) {
        msg = error.message;
      }
      enqueueSnackbar(msg, { variant: 'error' });
    },
  });

  // Export mutation
  const exportMutation = useMutation({
    mutationFn: async (params: { runId: number; sheetName: string }) => {
      return exportCoverageRun(params.runId, params.sheetName);
    },
    onSuccess: (data) => {
      enqueueSnackbar(`Exported to Google Sheets successfully!`, { variant: 'success' });
      if (data.spreadsheet_url) {
        window.open(data.spreadsheet_url, '_blank');
      }
      setShowExportDialog(false);
    },
    onError: (error: unknown) => {
      let msg = 'Export failed';
      if (error instanceof AxiosError) {
        const data = error.response?.data;
        if (data && typeof data === 'object' && 'error' in data && typeof data.error === 'string') {
          msg = data.error;
        } else if (error.message) {
          msg = error.message;
        }
      } else if (error instanceof Error) {
        msg = error.message;
      }
      enqueueSnackbar(msg, { variant: 'error' });
    },
  });

  // Download CSV handler
  const handleDownloadCSV = async (runId: number) => {
    try {
      const blob = await downloadCoverageRunCSV(runId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `coverage_run_${runId}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      enqueueSnackbar('CSV downloaded successfully!', { variant: 'success' });
    } catch (error: unknown) {
      let msg = 'Download failed';
      if (error instanceof AxiosError) {
        const data = error.response?.data;
        if (data && typeof data === 'object' && 'error' in data && typeof data.error === 'string') {
          msg = data.error;
        } else if (error.message) {
          msg = error.message;
        }
      } else if (error instanceof Error) {
        msg = error.message;
      }
      enqueueSnackbar(msg, { variant: 'error' });
    }
  };

  // Diagnose handler
  const handleDiagnose = async (runId: number) => {
    setLoadingDiagnosis(true);
    setShowDiagnosisDialog(true);
    try {
      const data = await diagnoseCoverageRun(runId);
      setDiagnosisData(data);
    } catch {
      enqueueSnackbar('Failed to generate diagnosis', { variant: 'error' });
      setShowDiagnosisDialog(false);
      setDiagnosisData(null);
    } finally {
      setLoadingDiagnosis(false);
    }
  };

  return {
    uploadMutation,
    importSheetsMutation,
    runMutation,
    exportMutation,
    handleDownloadCSV,
    handleDiagnose,
  };
}
