'use client';

import { useQuery } from '@tanstack/react-query';
import {
  listWordLists,
  getCoverageCost,
  getCredits,
  getCoverageRun,
  getProcessingHistory,
} from '@/lib/api';

export function useCoverageData(currentRunId: number | null) {
  // Load word lists
  const wordListsQuery = useQuery({
    queryKey: ['wordlists'],
    queryFn: listWordLists,
  });

  // Load coverage cost
  const costQuery = useQuery({
    queryKey: ['coverageCost'],
    queryFn: getCoverageCost,
    staleTime: 1000 * 60 * 60, // Cache for 1 hour
  });

  // Load user credits
  const creditsQuery = useQuery({
    queryKey: ['credits'],
    queryFn: getCredits,
    staleTime: 1000 * 60, // Refresh every minute
  });

  // Load coverage run results
  const runQuery = useQuery({
    queryKey: ['coverageRun', currentRunId],
    queryFn: () => getCoverageRun(currentRunId!),
    enabled: !!currentRunId,
    refetchOnWindowFocus: false,
    // Poll every 2 seconds if the run is still processing
    refetchInterval: (query) => {
      const run = query.state.data?.coverage_run;
      return run && (run.status === 'pending' || run.status === 'processing') ? 2000 : false;
    },
  });

  // Load processing history for source selection
  const historyQuery = useQuery({
    queryKey: ['history'],
    queryFn: getProcessingHistory,
    staleTime: 1000 * 60 * 5,
  });

  return {
    wordListsData: wordListsQuery.data,
    loadingWordLists: wordListsQuery.isLoading,
    costData: costQuery.data,
    creditsData: creditsQuery.data,
    runData: runQuery.data,
    loadingRun: runQuery.isLoading,
    historyData: historyQuery.data,
    loadingHistory: historyQuery.isLoading,
  };
}
