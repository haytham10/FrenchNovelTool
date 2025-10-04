import { useState, useEffect, useRef, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { Job } from '@/lib/api';
import { getAccessToken } from '@/lib/auth';

interface UseJobWebSocketProps {
  jobId: number | null;
  enabled?: boolean;
  onProgress?: (job: Job) => void;
  onComplete?: (job: Job) => void;
  onError?: (job: Job) => void;
  onCancel?: (job: Job) => void;
}

interface UseJobWebSocketReturn {
  job: Job | null;
  connected: boolean;
  error: Error | null;
}

/**
 * Custom hook to manage a WebSocket connection for real-time job updates.
 * It handles connection, events, and cleanup.
 *
 * @param {UseJobWebSocketProps} props - The properties for the hook.
 * @returns {UseJobWebSocketReturn} The state of the WebSocket connection and job data.
 */
export function useJobWebSocket({
  jobId,
  enabled = true,
  onProgress,
  onComplete,
  onError,
  onCancel,
}: UseJobWebSocketProps): UseJobWebSocketReturn {
  const [job, setJob] = useState<Job | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // Use a ref to store the callbacks. This prevents the useEffect hook
  // from re-running every time the parent component re-renders.
  const callbacksRef = useRef({ onProgress, onComplete, onError, onCancel });

  // Keep the callbacks in the ref up-to-date with the latest ones
  useEffect(() => {
    callbacksRef.current = { onProgress, onComplete, onError, onCancel };
  }, [onProgress, onComplete, onError, onCancel]);

  const handleJobProgress = useCallback((data: Job) => {
    setJob(data);
    console.log('Job progress received:', data);

    // Use the latest callbacks from the ref
    const { onProgress, onComplete, onError, onCancel } = callbacksRef.current;

    if (data.status === 'processing' && onProgress) {
      onProgress(data);
    } else if (data.status === 'completed' && onComplete) {
      onComplete(data);
    } else if (data.status === 'failed' && onError) {
      onError(data);
    } else if (data.status === 'cancelled' && onCancel) {
      onCancel(data);
    }
  }, []);

  useEffect(() => {
    if (!jobId || !enabled) {
      return;
    }
    const token = getAccessToken();
    if (!token) {
      console.log('No token found, WebSocket connection not established.');
      return;
    }

    const socket: Socket = io(process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000', {
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      query: {
        token: token,
      },
    });

    socket.on('connect', () => {
      console.log('WebSocket connected');
      setConnected(true);
      setError(null);
      // Join the job room
      // Include the JWT token in the join payload so the server can verify ownership
      socket.emit('join_job', { job_id: jobId, token });
    });

    socket.on('disconnect', (reason) => {
      console.log(`WebSocket disconnected: ${reason}`);
      setConnected(false);
      // Only set an error if it's not a clean disconnect
      if (reason !== 'io client disconnect') {
        setError(new Error(`WebSocket disconnected: ${reason}. Reconnecting...`));
      }
    });

    socket.on('connect_error', (err) => {
      console.error('WebSocket connection error:', err);
      setError(new Error(`Connection error: ${err.message}`));
      setConnected(false);
    });

    socket.on('error', (data: { message: string }) => {
      console.error('WebSocket error:', data.message);
      setError(new Error(data.message));
    });

    // Job progress event handler
    socket.on('job_progress', handleJobProgress);

    // Room status events
    socket.on('joined_room', (data) => {
      console.log(`Successfully joined room for job ${data.job_id}`);
      // You might want to fetch the initial job state here if needed
    });

    socket.on('left_room', (data) => {
      console.log(`Left room for job ${data.job_id}`);
    });

    // Cleanup on unmount or when dependencies change
    return () => {
      if (socket) {
        console.log(`Cleaning up WebSocket for job ${jobId}`);
        socket.emit('leave_job', { job_id: jobId });
        socket.disconnect();
      }
    };
    // The dependency array is now stable and won't cause re-renders.
  }, [jobId, enabled, handleJobProgress]);

  return {
    job,
    connected,
    error,
  };
}
