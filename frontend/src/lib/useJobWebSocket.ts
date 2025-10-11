import { useState, useEffect, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import type { Job } from '@/lib/types';
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
  
  // Store socket in ref for cleanup on page unload
  const socketRef = useRef<Socket | null>(null);

  // Use a ref to store the callbacks. This prevents the useEffect hook
  // from re-running every time the parent component re-renders.
  const callbacksRef = useRef({ onProgress, onComplete, onError, onCancel });

  // Keep the callbacks in the ref up-to-date with the latest ones
  useEffect(() => {
    callbacksRef.current = { onProgress, onComplete, onError, onCancel };
  }, [onProgress, onComplete, onError, onCancel]);
  
  // Cleanup on page unload to prevent memory leaks
  useEffect(() => {
    const handleUnload = () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
        socketRef.current = null;
      }
    };
    
    window.addEventListener('beforeunload', handleUnload);
    return () => window.removeEventListener('beforeunload', handleUnload);
  }, []);

  useEffect(() => {
    if (!jobId || !enabled) {
      return;
    }
    const token = getAccessToken();
    if (!token) {
      // No token available; do not establish WebSocket connection
      return;
    }

    const socket: Socket = io(process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000', {
      path: '/socket.io/',
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      query: {
        token: token,
      },
    });
    
    // Store socket in ref for cleanup
    socketRef.current = socket;

    const handleJobProgress = (data: Job) => {
      setJob(data);
      
      // Log progress updates for debugging (can be removed in production)
      console.debug(
        `[WebSocket] Job ${data.id}: ${data.progress_percent || 0}% - ${data.current_step || 'Initializing'} (${data.status})`
      );

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
    };

    socket.on('connect', () => {
      setConnected(true);
      setError(null);
      // Join the job room
      // Include the JWT token in the join payload so the server can verify ownership
      socket.emit('join_job', { job_id: jobId, token });
    });

    socket.on('disconnect', (reason) => {
      setConnected(false);
      // Only set an error if it's not a clean disconnect
      if (reason !== 'io client disconnect') {
        setError(new Error(`WebSocket disconnected: ${reason}. Reconnecting...`));
      }
    });

    socket.on('connect_error', (err) => {
      setError(new Error(`Connection error: ${err.message}`));
      setConnected(false);
    });

    socket.on('error', (data: { message: string }) => {
      setError(new Error(data.message));
    });

    // Job progress event handler
    socket.on('job_progress', handleJobProgress);

    // Room status events
    socket.on('joined_room', () => {
      // joined room - initial state can be fetched if required
    });

    socket.on('left_room', () => {
      // left room
    });

    // Cleanup on unmount or when dependencies change
    return () => {
      socket.emit('leave_job', { job_id: jobId });
      socket.disconnect();
      socketRef.current = null;
    };
    // Only recreate socket when jobId or enabled changes
  }, [jobId, enabled]);

  return {
    job,
    connected,
    error,
  };
}
