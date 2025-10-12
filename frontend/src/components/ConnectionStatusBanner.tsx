'use client';

import React, { useEffect, useState } from 'react';
import { Alert, Button, Box, Typography, Collapse } from '@mui/material';
import Icon from './Icon';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { useAuth } from './AuthContext';

export default function ConnectionStatusBanner() {
  const { user } = useAuth();
  const [showReconnect] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    // In a real app, you'd check token expiration or listen for 401 errors
    // For now, this is a placeholder
    const checkConnection = () => {
      // Simulate checking connection status
      // This would be replaced with actual API health check
      if (user) {
        // Check if token is about to expire
        // setShowReconnect(tokenNearExpiry);
      }
    };

    const interval = setInterval(checkConnection, 60000); // Check every minute
    return () => clearInterval(interval);
  }, [user]);

  if (!user || dismissed || !showReconnect) {
    return null;
  }

  const handleReconnect = () => {
    // Trigger OAuth flow
    window.location.href = '/login';
  };

  const handleDismiss = () => {
    setDismissed(true);
  };

  return (
    <Collapse in={showReconnect && !dismissed}>
      <Box sx={{ position: 'sticky', top: 64, zIndex: 1000 }}>
        <Alert
          severity="warning"
          icon={<Icon icon={AlertTriangle} />}
          action={
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                size="small"
                variant="outlined"
                color="inherit"
                onClick={handleReconnect}
                startIcon={<Icon icon={RefreshCw} fontSize="small" />}
              >
                Reconnect
              </Button>
              <Button size="small" color="inherit" onClick={handleDismiss}>
                Dismiss
              </Button>
            </Box>
          }
          sx={{ mb: 2, borderRadius: 0 }}
        >
          <Typography variant="body2" fontWeight={600}>
            Your Google connection is about to expire
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Please reconnect to continue using Sheets export and Drive features.
          </Typography>
        </Alert>
      </Box>
    </Collapse>
  );
}
