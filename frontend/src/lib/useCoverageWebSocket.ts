import { useState, useEffect, useRef, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import type { CoverageRun } from '@/lib/api';
import { getAccessToken } from '@/lib/auth';

interface UseCoverageWebSocketProps {
  runId: number | null;
  enabled?: boolean;
  onProgress?: (run: CoverageRun) => void;
  onComplete?: (run: CoverageRun) => void;
  onError?: (run: CoverageRun) => void;
  onCancel?: (run: CoverageRun) => void;
}

interface UseCoverageWebSocketReturn {
  run: CoverageRun | null;
  connected: boolean;
  error: Error | null;
}

/**
 * Subscribe to real-time coverage run updates via WebSocket.
 */
export function useCoverageWebSocket({
  runId,
  enabled = true,
  onProgress,
  onComplete,
  onError,
  onCancel,
}: UseCoverageWebSocketProps): UseCoverageWebSocketReturn {
  const [run, setRun] = useState<CoverageRun | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const callbacksRef = useRef({ onProgress, onComplete, onError, onCancel });
  useEffect(() => {
    callbacksRef.current = { onProgress, onComplete, onError, onCancel };
  }, [onProgress, onComplete, onError, onCancel]);

  const handleProgress = useCallback((data: CoverageRun) => {
    setRun(data);
    const { onProgress, onComplete, onError, onCancel } = callbacksRef.current;
    if (data.status === 'processing' && onProgress) onProgress(data);
    else if (data.status === 'completed' && onComplete) onComplete(data);
    else if (data.status === 'failed' && onError) onError(data);
    else if (data.status === 'cancelled' && onCancel) onCancel(data);
  }, []);

  useEffect(() => {
    if (!runId || !enabled) return;
    const token = getAccessToken();
    if (!token) return;

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
    const socket: Socket = io(apiUrl, {
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      // Some proxies or versions expect token in `auth` while others read query args on the server.
      // Provide both to maximize compatibility with the Flask-SocketIO server which checks both.
      auth: { token },
      query: { token },
    });

    socket.on('connect', () => {
      setConnected(true);
      setError(null);
      // Use the server-side event to join the run room
      socket.emit('join_coverage_run', { run_id: runId, token });
    });

    socket.on('disconnect', (reason) => {
      setConnected(false);
      if (reason !== 'io client disconnect') {
        setError(new Error(`WebSocket disconnected: ${reason}. Reconnecting...`));
      }
    });

    socket.on('connect_error', (err) => {
      setConnected(false);
      setError(new Error(`Connection error: ${err.message}`));
    });

    socket.on('error', (data: { message: string }) => {
      setError(new Error(data.message));
    });

    socket.on('coverage_progress', handleProgress);

    return () => {
      try {
        socket.emit('leave_coverage_run', { run_id: runId });
      } finally {
        socket.disconnect();
      }
    };
  }, [runId, enabled, handleProgress]);

  return { run, connected, error };
}
