/**
 * React Query hooks for API calls
 * Provides caching, background refetching, and optimistic updates
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';
import {
  processPdfAsync,
  exportToSheet,
  getProcessingHistory,
  getHistoryDetail,
  getHistoryChunks,
  exportHistoryToSheets,
  getUserSettings,
  updateUserSettings,
  retryHistoryEntry,
  duplicateHistoryEntry,
  getCredits,
  estimateCost,
  estimatePdfCost,
  confirmJob,
  finalizeJob,
  getJob,
  getApiErrorMessage,
  type ProcessPdfAsyncRequest,
  type Job,
  type ExportToSheetRequest,
  type ExportHistoryRequest,
  type UserSettings,
  type CostEstimateRequest,
  type EstimatePdfRequest,
  type JobConfirmRequest,
  type JobFinalizeRequest,
} from './api';

/**
 * Query Keys
 */
export const queryKeys = {
  history: ['history'] as const,
  historyDetail: (id: number) => ['history', id] as const,
  historyChunks: (id: number) => ['history', id, 'chunks'] as const,
  settings: ['settings'] as const,
  credits: ['credits'] as const,
  jobs: ['jobs'] as const,
};

/**
 * History Queries
 */
export function useHistory() {
  return useQuery({
    queryKey: queryKeys.history,
    queryFn: getProcessingHistory,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

export function useHistoryDetail(entryId: number | null) {
  return useQuery({
    queryKey: entryId ? queryKeys.historyDetail(entryId) : ['history', 'null'],
    queryFn: () => entryId ? getHistoryDetail(entryId) : Promise.resolve(null),
    enabled: !!entryId,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

export function useHistoryChunks(entryId: number | null) {
  return useQuery({
    queryKey: entryId ? queryKeys.historyChunks(entryId) : ['history', 'null', 'chunks'],
    queryFn: () => entryId ? getHistoryChunks(entryId) : Promise.resolve({ chunks: [] }),
    enabled: !!entryId,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

export function useExportHistoryToSheets() {
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();

  return useMutation({
    mutationFn: ({ entryId, data }: { entryId: number; data?: ExportHistoryRequest }) =>
      exportHistoryToSheets(entryId, data),
    
    onSuccess: (result, variables) => {
      // Invalidate history queries to refresh exported status
      queryClient.invalidateQueries({ queryKey: queryKeys.history });
      queryClient.invalidateQueries({ queryKey: queryKeys.historyDetail(variables.entryId) });
      
      enqueueSnackbar('Successfully exported to Google Sheets!', { variant: 'success' });
    },
    
    onError: (error) => {
      enqueueSnackbar(
        getApiErrorMessage(error, 'Failed to export to Google Sheets'),
        { variant: 'error' }
      );
    },
  });
}

/**
 * Settings Queries
 */
export function useSettings() {
  return useQuery({
    queryKey: queryKeys.settings,
    queryFn: getUserSettings,
    staleTime: 1000 * 60 * 10, // 10 minutes
  });
}

export function useUpdateSettings() {
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();

  return useMutation({
    mutationFn: (settings: Partial<UserSettings>) => updateUserSettings(settings),
    
    // Optimistic update
    onMutate: async (newSettings) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.settings });

      // Snapshot the previous value
      const previousSettings = queryClient.getQueryData<UserSettings>(queryKeys.settings);

      // Optimistically update to the new value
      queryClient.setQueryData<UserSettings>(queryKeys.settings, (old) => ({
        ...old!,
        ...newSettings,
      }));

      return { previousSettings };
    },
    
    // If mutation fails, use the context returned from onMutate to roll back
    onError: (error, _variables, context) => {
      if (context?.previousSettings) {
        queryClient.setQueryData(queryKeys.settings, context.previousSettings);
      }
      enqueueSnackbar(
        getApiErrorMessage(error, 'Failed to update settings'),
        { variant: 'error' }
      );
    },
    
    // Always refetch after error or success
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.settings });
    },
    
    onSuccess: () => {
      enqueueSnackbar('Settings updated successfully!', { variant: 'success' });
    },
  });
}

/**
 * PDF Processing Mutations
 */
export function useProcessPdf() {
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();

  return useMutation({
    mutationFn: (request: ProcessPdfAsyncRequest) => processPdfAsync(request),
    
    onSuccess: (data) => {
      enqueueSnackbar(`Processing started (Job ID: ${data.job_id})`, { variant: 'info' });
      // Invalidate history since we just started a new job
      queryClient.invalidateQueries({ queryKey: queryKeys.history });
    },
    
    onError: (error) => {
      enqueueSnackbar(
        getApiErrorMessage(error, 'Failed to start PDF processing'),
        { variant: 'error' }
      );
    },
  });
}

/**
 * Job Status Polling
 */
export function useJobStatus(jobId: number | null, options?: { enabled?: boolean; refetchInterval?: number }) {
  return useQuery({
    queryKey: ['job-status', jobId],
    queryFn: () => getJob(jobId!),
    enabled: !!jobId && (options?.enabled ?? true),
    refetchInterval: (query) => {
      const data = query.state.data as Job | undefined;
      // Stop polling when job is completed, failed, or cancelled
      if (data?.status === 'completed' || data?.status === 'failed' || data?.status === 'cancelled') {
        return false;
      }
      return options?.refetchInterval ?? 2000; // Poll every 2 seconds by default
    },
  });
}

/**
 * Export Mutations
 */
export function useExportToSheet() {
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();

  return useMutation({
    mutationFn: (data: ExportToSheetRequest) => exportToSheet(data),
    
    onSuccess: () => {
      enqueueSnackbar('Exported to Google Sheets successfully!', { variant: 'success' });
      // Invalidate history to refresh the spreadsheet_url
      queryClient.invalidateQueries({ queryKey: queryKeys.history });
    },
    
    onError: (error) => {
      enqueueSnackbar(
        getApiErrorMessage(error, 'Failed to export to Google Sheets'),
        { variant: 'error' }
      );
    },
  });
}

/**
 * Retry History Entry Mutation
 */
export function useRetryHistoryEntry() {
  const { enqueueSnackbar } = useSnackbar();

  return useMutation({
    mutationFn: (entryId: number) => retryHistoryEntry(entryId),
    
    onSuccess: (data) => {
      enqueueSnackbar(data.message || 'Retry information retrieved', { variant: 'info' });
    },
    
    onError: (error) => {
      enqueueSnackbar(
        getApiErrorMessage(error, 'Failed to retry entry'),
        { variant: 'error' }
      );
    },
  });
}

/**
 * Duplicate History Entry Mutation
 */
export function useDuplicateHistoryEntry() {
  const { enqueueSnackbar } = useSnackbar();

  return useMutation({
    mutationFn: (entryId: number) => duplicateHistoryEntry(entryId),
    
    onSuccess: (data) => {
      enqueueSnackbar(data.message || 'Settings retrieved for duplication', { variant: 'info' });
    },
    
    onError: (error) => {
      enqueueSnackbar(
        getApiErrorMessage(error, 'Failed to duplicate entry'),
        { variant: 'error' }
      );
    },
  });
}

/**
 * Credit Queries
 */
export function useCredits() {
  return useQuery({
    queryKey: queryKeys.credits,
    queryFn: getCredits,
    staleTime: 1000 * 60 * 5, // 5 minutes
    refetchOnWindowFocus: true,
  });
}

export function useJob(jobId: number | null | undefined) {
  return useQuery({
    queryKey: [...queryKeys.jobs, jobId],
    queryFn: () => (jobId ? getJob(jobId) : null),
    enabled: !!jobId,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

/**
 * Credit Mutations
 */
export function useEstimateCost() {
  return useMutation({
    mutationFn: (request: CostEstimateRequest) => estimateCost(request),
  });
}

export function useEstimatePdfCost() {
  return useMutation({
    mutationFn: (request: EstimatePdfRequest) => estimatePdfCost(request),
  });
}

export function useConfirmJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: JobConfirmRequest) => confirmJob(request),
    onSuccess: () => {
      // Invalidate credits to refresh balance
      queryClient.invalidateQueries({ queryKey: queryKeys.credits });
    },
  });
}

export function useFinalizeJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ jobId, request }: { jobId: number; request: JobFinalizeRequest }) =>
      finalizeJob(jobId, request),
    onSuccess: () => {
      // Invalidate credits and history to refresh
      queryClient.invalidateQueries({ queryKey: queryKeys.credits });
      queryClient.invalidateQueries({ queryKey: queryKeys.history });
    },
  });
}
