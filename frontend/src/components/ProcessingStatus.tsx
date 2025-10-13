import React from 'react';
import {
  Box,
  Typography,
  CircularProgress,
  Alert,
  AlertTitle,
  Button,
  LinearProgress,
  Chip,
} from '@mui/material';
import { 
  ErrorOutline, 
  CheckCircle, 
  Refresh,
  Info,
} from '@mui/icons-material';
import { 
  getErrorMessage, 
  getErrorSuggestion, 
  isErrorActionable 
} from '@/lib/errorMessages';

export interface ProcessingStatusProps {
  status: 'idle' | 'processing' | 'completed' | 'failed';
  progress?: number;
  currentStep?: string;
  errorCode?: string;
  errorMessage?: string;
  fileName?: string;
  onRetry?: () => void;
  onReset?: () => void;
  className?: string;
}

export function ProcessingStatus({
  status,
  progress = 0,
  currentStep = 'Processing...',
  errorCode,
  errorMessage,
  fileName,
  onRetry,
  onReset,
  className,
}: ProcessingStatusProps) {
  // Handle error states with user-friendly messages
  if (status === 'failed') {
    const friendlyError = getErrorMessage(errorCode || 'UNKNOWN_ERROR');
    const suggestion = getErrorSuggestion(errorCode);
    const actionable = isErrorActionable(errorCode);
    const displayMessage = errorMessage || friendlyError.message;

    return (
      <Box className={className}>
        <Alert 
          severity="error"
          icon={<ErrorOutline fontSize="large" />}
          sx={{ 
            mb: 2,
            '& .MuiAlert-message': {
              width: '100%'
            }
          }}
        >
          <AlertTitle sx={{ fontWeight: 600, mb: 1 }}>
            Processing Failed
          </AlertTitle>
          
          <Typography variant="body2" sx={{ mb: 2 }}>
            {displayMessage}
          </Typography>
          
          {suggestion && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1, fontWeight: 500 }}>
                <Info sx={{ fontSize: 16, mr: 0.5, verticalAlign: 'text-bottom' }} />
                What you can do:
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {suggestion}
              </Typography>
            </Box>
          )}
          
          {errorCode && (
            <Box sx={{ mb: 2 }}>
              <Chip 
                label={`Error Code: ${errorCode}`} 
                size="small" 
                variant="outlined" 
                color="error"
              />
            </Box>
          )}
          
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {actionable && onRetry && (
              <Button
                size="small"
                variant="contained"
                color="primary"
                onClick={onRetry}
                startIcon={<Refresh />}
              >
                Try Again
              </Button>
            )}
            {onReset && (
              <Button
                size="small"
                variant="outlined"
                onClick={onReset}
              >
                Start Over
              </Button>
            )}
          </Box>
        </Alert>
      </Box>
    );
  }

  // Handle completed state
  if (status === 'completed') {
    return (
      <Box className={className}>
        <Alert 
          severity="success"
          icon={<CheckCircle fontSize="large" />}
          sx={{ mb: 2 }}
        >
          <AlertTitle sx={{ fontWeight: 600 }}>
            Processing Complete!
          </AlertTitle>
          <Typography variant="body2">
            {fileName ? `Successfully processed "${fileName}"` : 'Your file has been processed successfully.'}
          </Typography>
        </Alert>
      </Box>
    );
  }

  // Handle processing state
  if (status === 'processing') {
    return (
      <Box className={className}>
        <Box 
          display="flex" 
          flexDirection="column" 
          alignItems="center" 
          py={4}
          sx={{
            minHeight: '200px',
            justifyContent: 'center',
          }}
        >
          {/* Progress Circle */}
          <Box
            sx={{
              position: 'relative',
              display: 'inline-flex',
              mb: 3,
            }}
          >
            <CircularProgress 
              size={64} 
              thickness={4}
              sx={{
                color: 'primary.main',
              }}
            />
            <Box
              sx={{
                position: 'absolute',
                top: 0,
                left: 0,
                bottom: 0,
                right: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Typography
                variant="caption"
                component="div"
                color="primary"
                fontWeight={600}
              >
                {progress > 0 ? `${Math.round(progress)}%` : ''}
              </Typography>
            </Box>
          </Box>

          {/* Status Text */}
          <Typography 
            variant="h6" 
            color="textPrimary" 
            sx={{ 
              fontWeight: 500,
              mb: 1,
              textAlign: 'center',
            }}
          >
            {currentStep}
          </Typography>
          
          <Typography 
            variant="body2" 
            color="text.secondary"
            sx={{ textAlign: 'center', mb: 2 }}
          >
            {fileName ? `Processing "${fileName}"...` : 'Please wait while we process your file...'}
          </Typography>

          {/* Progress Bar */}
          {progress > 0 && (
            <Box sx={{ width: '100%', maxWidth: 300 }}>
              <LinearProgress 
                variant="determinate" 
                value={progress} 
                sx={{ 
                  height: 8, 
                  borderRadius: 4,
                  backgroundColor: 'action.hover',
                  '& .MuiLinearProgress-bar': {
                    borderRadius: 4,
                  }
                }} 
              />
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  0%
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  100%
                </Typography>
              </Box>
            </Box>
          )}
        </Box>
      </Box>
    );
  }

  // Idle state - no status to show
  return null;
}

export default ProcessingStatus;