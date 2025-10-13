/**
 * Demo page to test user-friendly error messages
 * Access via /error-demo
 */

'use client';

import React, { useState } from 'react';
import {
  Box,
  Container,
  Typography,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Paper,
  Divider,
} from '@mui/material';
import ProcessingStatus from '@/components/ProcessingStatus';
import { getErrorMessage, getEnhancedApiErrorMessage } from '@/lib/errorMessages';
import { useSnackbar } from 'notistack';

const ERROR_CODES = [
  'INVALID_PDF',
  'PDF_CORRUPTED', 
  'NO_TEXT',
  'GEMINI_API_ERROR',
  'RATE_LIMIT_EXCEEDED',
  'INSUFFICIENT_CREDITS',
  'GOOGLE_PERMISSION_ERROR',
  'SERVER_ERROR',
  'NETWORK_ERROR',
  'UNKNOWN_ERROR'
];

export default function ErrorDemoPage() {
  const [selectedErrorCode, setSelectedErrorCode] = useState('INVALID_PDF');
  const [processingStatus, setProcessingStatus] = useState<'idle' | 'processing' | 'completed' | 'failed'>('idle');
  const [progress, setProgress] = useState(0);
  const { enqueueSnackbar } = useSnackbar();

  const handleTestError = () => {
    setProcessingStatus('failed');
  };

  const handleTestProcessing = () => {
    setProcessingStatus('processing');
    setProgress(0);
    
    // Simulate progress
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setProcessingStatus('completed');
          return 100;
        }
        return prev + 10;
      });
    }, 500);
  };

  const handleTestSnackbar = () => {
    const enhancedError = getEnhancedApiErrorMessage({
      response: {
        data: {
          error_code: selectedErrorCode,
          error_message: 'Test error message'
        }
      }
    });
    
    enqueueSnackbar(enhancedError.message, { variant: 'error' });
    
    if (enhancedError.suggestion && enhancedError.actionable) {
      setTimeout(() => {
        enqueueSnackbar(enhancedError.suggestion!, { 
          variant: 'info',
          autoHideDuration: 8000 
        });
      }, 1000);
    }
  };

  const handleRetry = () => {
    enqueueSnackbar('Retry clicked!', { variant: 'info' });
    setProcessingStatus('idle');
    setProgress(0);
  };

  const handleReset = () => {
    enqueueSnackbar('Reset clicked!', { variant: 'info' });
    setProcessingStatus('idle');
    setProgress(0);
  };

  const errorInfo = getErrorMessage(selectedErrorCode);

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h4" gutterBottom>
        Error Handling Demo
      </Typography>
      
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Test the user-friendly error messages and ProcessingStatus component.
      </Typography>

      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" gutterBottom>
          Error Code Configuration
        </Typography>
        
        <FormControl fullWidth sx={{ mb: 3 }}>
          <InputLabel>Select Error Code</InputLabel>
          <Select
            value={selectedErrorCode}
            onChange={(e) => setSelectedErrorCode(e.target.value)}
            label="Select Error Code"
          >
            {ERROR_CODES.map((code) => (
              <MenuItem key={code} value={code}>
                {code}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            Error Message Preview:
          </Typography>
          <Typography variant="body2" sx={{ mb: 1 }}>
            <strong>Message:</strong> {errorInfo.message}
          </Typography>
          <Typography variant="body2" sx={{ mb: 1 }}>
            <strong>Suggestion:</strong> {errorInfo.suggestion || 'None'}
          </Typography>
          <Typography variant="body2">
            <strong>Actionable:</strong> {errorInfo.actionable ? 'Yes' : 'No'}
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <Button
            variant="contained"
            color="error"
            onClick={handleTestError}
          >
            Test Error Status
          </Button>
          <Button
            variant="contained"
            color="primary"
            onClick={handleTestProcessing}
          >
            Test Processing
          </Button>
          <Button
            variant="outlined"
            onClick={handleTestSnackbar}
          >
            Test Snackbar
          </Button>
        </Box>
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          ProcessingStatus Component
        </Typography>
        
        <Divider sx={{ my: 2 }} />
        
        <ProcessingStatus
          status={processingStatus}
          progress={progress}
          currentStep={processingStatus === 'processing' ? 'Processing your PDF...' : ''}
          errorCode={processingStatus === 'failed' ? selectedErrorCode : undefined}
          fileName="demo-file.pdf"
          onRetry={handleRetry}
          onReset={handleReset}
        />
        
        {processingStatus === 'idle' && (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Typography variant="body2" color="text.secondary">
              Click a test button above to see the ProcessingStatus component in action.
            </Typography>
          </Box>
        )}
      </Paper>
    </Container>
  );
}