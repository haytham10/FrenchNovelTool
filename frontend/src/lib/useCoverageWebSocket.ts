import { useState, useEffect, useRef } from 'react';
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
  
  // Store socket in ref for cleanup on page unload
  const socketRef = useRef<Socket | null>(null);

  // Use refs to store the latest callbacks without triggering reconnects
  const callbacksRef = useRef({ onProgress, onComplete, onError, onCancel });

  // Update refs when callbacks change (without recreating socket)
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
    if (!runId || !enabled) return;
    const token = getAccessToken();
    if (!token) return;

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
    const socket: Socket = io(apiUrl, {
      path: '/socket.io/',
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      // Some proxies or versions expect token in `auth` while others read query args on the server.
      // Provide both to maximize compatibility with the Flask-SocketIO server which checks both.
      auth: { token },
      query: { token },
    });
    
    // Store socket in ref for cleanup
    socketRef.current = socket;

    const handleProgress = (data: CoverageRun) => {
      setRun(data);
      const callbacks = callbacksRef.current;
      if (data.status === 'processing' && callbacks.onProgress) callbacks.onProgress(data);
      else if (data.status === 'completed' && callbacks.onComplete) callbacks.onComplete(data);
      else if (data.status === 'failed' && callbacks.onError) callbacks.onError(data);
      else if (data.status === 'cancelled' && callbacks.onCancel) callbacks.onCancel(data);
    };

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
      // Clean disconnect: leave room first, then disconnect
      socket.emit('leave_coverage_run', { run_id: runId });
      socket.disconnect();
      socketRef.current = null;
    };
  }, [runId, enabled]); // Only recreate socket when runId or enabled changes

  return { run, connected, error };
}
