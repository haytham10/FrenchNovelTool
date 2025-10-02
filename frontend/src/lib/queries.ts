/**
 * React Query hooks for API calls
 * Provides caching, background refetching, and optimistic updates
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';
import {
  processPdf,
  exportToSheet,
  getProcessingHistory,
  getUserSettings,
  updateUserSettings,
  getApiErrorMessage,
  type ProcessPdfOptions,
  type ExportToSheetRequest,
  type UserSettings,
} from './api';

/**
 * Query Keys
 */
export const queryKeys = {
  history: ['history'] as const,
  settings: ['settings'] as const,
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
    mutationFn: ({ file, options }: { file: File; options?: ProcessPdfOptions }) =>
      processPdf(file, options),
    
    onSuccess: () => {
      // Invalidate history since we just processed a new file
      queryClient.invalidateQueries({ queryKey: queryKeys.history });
    },
    
    onError: (error) => {
      enqueueSnackbar(
        getApiErrorMessage(error, 'Failed to process PDF'),
        { variant: 'error' }
      );
    },
  });
}

/**
 * Export Mutations
 */
export function useExportToSheet() {
  const { enqueueSnackbar } = useSnackbar();

  return useMutation({
    mutationFn: (data: ExportToSheetRequest) => exportToSheet(data),
    
    onSuccess: () => {
      enqueueSnackbar('Exported to Google Sheets successfully!', { variant: 'success' });
    },
    
    onError: (error) => {
      enqueueSnackbar(
        getApiErrorMessage(error, 'Failed to export to Google Sheets'),
        { variant: 'error' }
      );
    },
  });
}
