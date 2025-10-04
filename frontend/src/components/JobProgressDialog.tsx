/**
 * Job Progress Dialog - Shows async PDF processing progress with real-time WebSocket updates
 */
import React from 'react';
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
  Chip,
  Stack,
} from '@mui/material';
import { CheckCircle, Error as ErrorIcon, Cancel, HourglassEmpty, WifiOff } from '@mui/icons-material';
import { Job, cancelJob } from '@/lib/api';
import { useJobWebSocket } from '@/lib/useJobWebSocket';

interface JobProgressDialogProps {
  jobId: number | null;
  open: boolean;
  onClose: () => void;
  onComplete?: (job: Job) => void;
  onError?: (job: Job) => void;
}

export default function JobProgressDialog({
  jobId,
  open,
  onClose,
  onComplete,
  onError,
}: JobProgressDialogProps) {
  const [cancelling, setCancelling] = React.useState(false);

  const { job, connected, error } = useJobWebSocket({
    jobId,
    enabled: open && jobId !== null,
    onComplete: (completedJob) => {
      if (onComplete) {
        onComplete(completedJob);
      }
    },
    onError: (failedJob) => {
      if (onError) {
        onError(failedJob);
      }
    },
  });

  const handleCancel = async () => {
    if (!jobId || cancelling) return;

    try {
      setCancelling(true);
      await cancelJob(jobId);
      // The WebSocket will detect the cancelled status
    } catch (err) {
      console.error('Failed to cancel job:', err);
      setCancelling(false);
    }
  };

  const getStatusIcon = () => {
    if (!job) return <HourglassEmpty color="disabled" />;

    switch (job.status) {
      case 'completed':
        return <CheckCircle color="success" />;
      case 'failed':
        return <ErrorIcon color="error" />;
      case 'cancelled':
        return <Cancel color="warning" />;
      default:
        return <HourglassEmpty color="primary" />;
    }
  };

  const getStatusColor = (): 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' => {
    if (!job) return 'default';

    switch (job.status) {
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      case 'cancelled':
        return 'warning';
      case 'processing':
        return 'primary';
      default:
        return 'default';
    }
  };

  const canCancel = job && ['pending', 'processing'].includes(job.status);
  const isTerminal = job && ['completed', 'failed', 'cancelled'].includes(job.status);
  const progressPercent = job?.progress_percent ?? 0;

  return (
    <Dialog open={open} onClose={isTerminal ? onClose : undefined} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Stack direction="row" alignItems="center" spacing={2}>
          {getStatusIcon()}
          <Typography variant="h6">PDF Processing</Typography>
          <Chip
            label={job?.status ?? 'initializing'}
            color={getStatusColor()}
            size="small"
          />
          {!connected && job && job.status === 'processing' && (
            <Chip
              icon={<WifiOff />}
              label="Reconnecting..."
              color="warning"
              size="small"
              variant="outlined"
            />
          )}
        </Stack>
      </DialogTitle>

      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error.message}
          </Alert>
        )}

        {job && (
          <Stack spacing={2}>
            {/* Filename */}
            <Typography variant="body2" color="text.secondary">
              File: <strong>{job.original_filename}</strong>
            </Typography>

            {/* Progress bar */}
            {job.status === 'processing' && (
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    {job.current_step || 'Processing...'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {progressPercent}%
                  </Typography>
                </Box>
                <LinearProgress variant="determinate" value={progressPercent} />
              </Box>
            )}

            {/* Chunk progress */}
            {job.total_chunks && job.total_chunks > 1 && (
              <Typography variant="body2" color="text.secondary">
                Chunks: {job.processed_chunks || 0} / {job.total_chunks}
              </Typography>
            )}

            {/* Error message */}
            {job.status === 'failed' && job.error_message && (
              <Alert severity="error">{job.error_message}</Alert>
            )}

            {/* Success metrics */}
            {job.status === 'completed' && (
              <Alert severity="success">
                Processing completed successfully!
                {job.processing_time_seconds && (
                  <Typography variant="caption" display="block">
                    Time: {job.processing_time_seconds}s
                  </Typography>
                )}
                {job.gemini_tokens_used && (
                  <Typography variant="caption" display="block">
                    Tokens used: {job.gemini_tokens_used.toLocaleString()}
                  </Typography>
                )}
              </Alert>
            )}

            {/* Failed chunks warning */}
            {job.failed_chunks && job.failed_chunks.length > 0 && (
              <Alert severity="warning">
                {job.failed_chunks.length} chunk(s) failed to process
              </Alert>
            )}
          </Stack>
        )}

        {!job && !error && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
            <Typography variant="body2" color="text.secondary">
              {connected ? 'Waiting for job data...' : 'Connecting...'}
            </Typography>
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        {canCancel && (
          <Button
            onClick={handleCancel}
            color="error"
            disabled={cancelling}
          >
            {cancelling ? 'Cancelling...' : 'Cancel Job'}
          </Button>
        )}
        {isTerminal && (
          <Button onClick={onClose} color="primary" variant="contained">
            Close
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
