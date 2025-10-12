/**
 * Custom hook for polling job status
 */
import { useState, useEffect, useCallback } from 'react';
import { getJob } from '@/lib/api';
import type { Job } from '@/lib/types';

interface UseJobPollingOptions {
  jobId: number | null;
  interval?: number; // Polling interval in milliseconds (default: 2000)
  enabled?: boolean; // Whether to enable polling
  onComplete?: (job: Job) => void;
  onError?: (job: Job) => void;
  onCancel?: (job: Job) => void;
}

interface UseJobPollingResult {
  job: Job | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export function useJobPolling({
  jobId,
  interval = 2000,
  enabled = true,
  onComplete,
  onError,
  onCancel,
}: UseJobPollingOptions): UseJobPollingResult {
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchJob = useCallback(async () => {
    if (!jobId) return;

    try {
      setLoading(true);
      setError(null);
      const jobData = await getJob(jobId);
      setJob(jobData);

      // Check terminal states
      if (jobData.status === 'completed' && onComplete) {
        onComplete(jobData);
      } else if (jobData.status === 'failed' && onError) {
        onError(jobData);
      } else if (jobData.status === 'cancelled' && onCancel) {
        onCancel(jobData);
      }
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch job'));
    } finally {
      setLoading(false);
    }
  }, [jobId, onComplete, onError, onCancel]);

  useEffect(() => {
    if (!enabled || !jobId) return;

    // Initial fetch
    fetchJob();

    // Set up polling only if job is not in terminal state
    const isTerminalState = job?.status && ['completed', 'failed', 'cancelled'].includes(job.status);
    
    if (!isTerminalState) {
      const intervalId = setInterval(() => {
        fetchJob();
      }, interval);

      return () => clearInterval(intervalId);
    }
  }, [jobId, enabled, interval, fetchJob, job?.status]);

  return {
    job,
    loading,
    error,
    refetch: fetchJob,
  };
}
