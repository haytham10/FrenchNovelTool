/**
 * JobProgressDialog - Shows progress of async PDF processing jobs
 */

import React, { useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  LinearProgress,
  Typography,
  Box,
  Alert,
} from '@mui/material';
import { useJobStatus } from '@/lib/queries';

interface JobProgressDialogProps {
  open: boolean;
  jobId: number | null;
  onClose: () => void;
  onComplete?: (result: { sentences_count?: number; spreadsheet_url?: string }) => void;
}

export default function JobProgressDialog({
  open,
  jobId,
  onClose,
  onComplete,
}: JobProgressDialogProps) {
  const { data: jobStatus, isLoading, error } = useJobStatus(jobId, { enabled: open && !!jobId });

  const job = jobStatus?.job;
  const result = jobStatus?.result;

  // Call onComplete when job is done
  useEffect(() => {
    if (job?.status === 'completed' && result && onComplete) {
      onComplete(result);
    }
  }, [job?.status, result, onComplete]);

  const getStatusMessage = () => {
    if (!job) return 'Loading...';
    
    switch (job.status) {
      case 'queued':
        return 'Job queued, waiting to start...';
      case 'processing':
        if (job.total_chunks && job.total_chunks > 1) {
          return `Processing chunk ${job.completed_chunks || 0} of ${job.total_chunks}...`;
        }
        return 'Processing PDF...';
      case 'completed':
        return 'Processing completed successfully!';
      case 'failed':
        return 'Processing failed';
      case 'cancelled':
        return 'Processing cancelled';
      default:
        return 'Preparing...';
    }
  };

  const getProgress = () => {
    if (!job) return 0;
    if (job.progress_percent !== undefined && job.progress_percent !== null) {
      return job.progress_percent;
    }
    if (job.status === 'completed') return 100;
    if (job.status === 'processing') return 50;
    if (job.status === 'queued') return 10;
    return 0;
  };

  const isJobFinished = job?.status === 'completed' || job?.status === 'failed' || job?.status === 'cancelled';

  return (
    <Dialog open={open} onClose={isJobFinished ? onClose : undefined} maxWidth="sm" fullWidth>
      <DialogTitle>
        {job?.original_filename || 'Processing PDF'}
      </DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Failed to load job status: {error instanceof Error ? error.message : 'Unknown error'}
          </Alert>
        )}

        {job?.error_message && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {job.error_message}
          </Alert>
        )}

        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {getStatusMessage()}
          </Typography>
          <LinearProgress
            variant="determinate"
            value={getProgress()}
            sx={{ mt: 1, height: 8, borderRadius: 1 }}
          />
          <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
            {Math.round(getProgress())}%
          </Typography>
        </Box>

        {job?.total_chunks && job.total_chunks > 1 && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Processing large PDF in {job.total_chunks} chunks of {job.chunk_size} pages each
            </Typography>
            {job.page_count && (
              <Typography variant="caption" color="text.secondary">
                Total pages: {job.page_count}
              </Typography>
            )}
          </Box>
        )}

        {job?.status === 'completed' && result && (
          <Alert severity="success" sx={{ mt: 2 }}>
            Successfully processed {result.sentences_count || 0} sentences!
          </Alert>
        )}
      </DialogContent>
      <DialogActions>
        {isJobFinished && (
          <Button onClick={onClose} variant="contained">
            Close
          </Button>
        )}
        {!isJobFinished && (
          <Button onClick={onClose} color="secondary">
            Run in Background
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
