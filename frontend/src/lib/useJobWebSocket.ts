/**
 * Custom hook for WebSocket-based real-time job progress updates
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import { getAccessToken } from '@/lib/auth';
import { Job } from '@/lib/api';

// Get WebSocket URL from API URL
const getWebSocketUrl = (): string => {
  const apiUrl =
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    'http://localhost:5000';
  
  // Remove /api/v1 suffix if present
  return apiUrl.replace(/\/api\/v\d+$/, '');
};

interface UseJobWebSocketOptions {
  jobId: number | null;
  enabled?: boolean;
  onComplete?: (job: Job) => void;
  onError?: (job: Job) => void;
  onCancel?: (job: Job) => void;
  onProgress?: (job: Job) => void;
}

interface UseJobWebSocketResult {
  job: Job | null;
  connected: boolean;
  error: Error | null;
}

export function useJobWebSocket({
  jobId,
  enabled = true,
  onComplete,
  onError,
  onCancel,
  onProgress,
}: UseJobWebSocketOptions): UseJobWebSocketResult {
  const [job, setJob] = useState<Job | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const socketRef = useRef<Socket | null>(null);

  const handleJobProgress = useCallback((jobData: Job) => {
    setJob(jobData);
    
    // Call progress callback
    if (onProgress) {
      onProgress(jobData);
    }

    // Check terminal states
    if (jobData.status === 'completed' && onComplete) {
      onComplete(jobData);
    } else if (jobData.status === 'failed' && onError) {
      onError(jobData);
    } else if (jobData.status === 'cancelled' && onCancel) {
      onCancel(jobData);
    }
  }, [onComplete, onError, onCancel, onProgress]);

  useEffect(() => {
    if (!enabled || !jobId) {
      // Cleanup socket if disabled or no job
      if (socketRef.current) {
        socketRef.current.disconnect();
        socketRef.current = null;
        setConnected(false);
      }
      return;
    }

    const token = getAccessToken();
    if (!token) {
      setError(new Error('No authentication token available'));
      return;
    }

    // Create socket connection
    const socket = io(getWebSocketUrl(), {
      auth: { token },
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    socketRef.current = socket;

    // Connection event handlers
    socket.on('connect', () => {
      console.log('WebSocket connected');
      setConnected(true);
      setError(null);

      // Join the job room
      socket.emit('join_job', { job_id: jobId, token });
    });

    socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      setConnected(false);
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

    // Cleanup on unmount
    return () => {
      if (socket) {
        socket.emit('leave_job', { job_id: jobId });
        socket.disconnect();
      }
    };
  }, [jobId, enabled, handleJobProgress]);

  return {
    job,
    connected,
    error,
  };
}
