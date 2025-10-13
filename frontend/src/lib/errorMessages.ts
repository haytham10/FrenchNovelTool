/**
 * User-friendly error messages for the French Novel Tool
 * Maps backend error codes to human-readable messages with actionable advice
 */

export interface ErrorMessage {
  message: string;
  suggestion?: string;
  actionable?: boolean;
}

export const ERROR_MESSAGES: Record<string, ErrorMessage> = {
  // PDF Processing Errors
  'INVALID_PDF': {
    message: 'This PDF appears corrupted or invalid.',
    suggestion: 'Please try another PDF file. Ensure it contains readable text (not just scanned images).',
    actionable: true
  },
  
  'PDF_CORRUPTED': {
    message: 'This PDF appears corrupted.',
    suggestion: 'Please try another file or use a different PDF viewer to save a clean copy.',
    actionable: true
  },
  
  'NO_TEXT': {
    message: 'This PDF contains no extractable text.',
    suggestion: 'This file may contain only scanned images. Try using OCR software to convert it to searchable text first.',
    actionable: true
  },
  
  'PDF_TOO_LARGE': {
    message: 'This PDF file is too large to process.',
    suggestion: 'Please split the PDF into smaller sections or compress it before uploading.',
    actionable: true
  },
  
  // AI Service Errors
  'GEMINI_API_ERROR': {
    message: 'The AI service is temporarily unavailable.',
    suggestion: 'Please try again in a few minutes. If the problem persists, check our status page.',
    actionable: true
  },
  
  'GEMINI_RESPONSE_ERROR': {
    message: 'The AI service returned an unexpected response.',
    suggestion: 'This may be due to unusual content in your PDF. Please try again or contact support.',
    actionable: true
  },
  
  // Rate Limiting & Quota Errors
  'RATE_LIMIT_EXCEEDED': {
    message: 'Processing limit reached.',
    suggestion: 'Please wait a few minutes before trying again. Consider upgrading your plan for higher limits.',
    actionable: true
  },
  
  'QUOTA_EXCEEDED': {
    message: 'Your daily processing quota has been exceeded.',
    suggestion: 'Your quota will reset at midnight UTC, or you can upgrade your plan for more processing capacity.',
    actionable: true
  },
  
  'INSUFFICIENT_CREDITS': {
    message: 'Insufficient credits to process this PDF.',
    suggestion: 'Please purchase more credits or try processing a smaller PDF file.',
    actionable: true
  },
  
  // Job & Processing Errors
  'JOB_NOT_FOUND': {
    message: 'Processing job not found.',
    suggestion: 'This job may have expired. Please start a new processing request.',
    actionable: true
  },
  
  'INVALID_JOB_STATUS': {
    message: 'Invalid processing status.',
    suggestion: 'Please refresh the page and try again. If the problem persists, start a new job.',
    actionable: true
  },
  
  'PROCESSING_ERROR': {
    message: 'An error occurred during processing.',
    suggestion: 'This could be due to unusual PDF content or temporary server issues. Please try again.',
    actionable: true
  },
  
  'TIMEOUT_ERROR': {
    message: 'Processing took too long and timed out.',
    suggestion: 'This PDF may be too complex. Try splitting it into smaller sections.',
    actionable: true
  },
  
  // Google Services Errors
  'GOOGLE_AUTH_ERROR': {
    message: 'Google authentication failed.',
    suggestion: 'Please sign out and sign back in to refresh your Google permissions.',
    actionable: true
  },
  
  'GOOGLE_DRIVE_ERROR': {
    message: 'Unable to access Google Drive.',
    suggestion: 'Please check your Google Drive permissions and ensure you have sufficient storage space.',
    actionable: true
  },
  
  'GOOGLE_SHEETS_ERROR': {
    message: 'Failed to export to Google Sheets.',
    suggestion: 'Please ensure you have edit permissions for Google Sheets and try again.',
    actionable: true
  },
  
  'GOOGLE_PERMISSION_ERROR': {
    message: 'Access denied to Google services.',
    suggestion: 'Please grant the necessary Google Drive and Sheets permissions and try again.',
    actionable: true
  },
  
  // Network & Server Errors
  'NETWORK_ERROR': {
    message: 'Unable to connect to the server.',
    suggestion: 'Please check your internet connection and try again.',
    actionable: true
  },
  
  'SERVER_ERROR': {
    message: 'A server error occurred.',
    suggestion: 'Our team has been notified. Please try again in a few minutes.',
    actionable: false
  },
  
  'SERVICE_UNAVAILABLE': {
    message: 'The service is temporarily unavailable.',
    suggestion: 'We are performing maintenance. Please try again in a few minutes.',
    actionable: false
  },
  
  // Validation Errors
  'INVALID_FILE_TYPE': {
    message: 'Invalid file type.',
    suggestion: 'Please upload a PDF file only.',
    actionable: true
  },
  
  'FILE_TOO_LARGE': {
    message: 'File size exceeds the maximum limit.',
    suggestion: 'Please upload a smaller PDF file (maximum 50MB).',
    actionable: true
  },
  
  'INVALID_SETTINGS': {
    message: 'Invalid processing settings.',
    suggestion: 'Please check your settings and ensure all values are within acceptable ranges.',
    actionable: true
  },
  
  // Coverage Analysis Errors
  'COVERAGE_ERROR': {
    message: 'Coverage analysis failed.',
    suggestion: 'Please try again with a different word list or smaller text sample.',
    actionable: true
  },
  
  'WORDLIST_ERROR': {
    message: 'Error loading word list.',
    suggestion: 'Please check that your word list is properly formatted and try again.',
    actionable: true
  },
  
  // Generic Fallbacks
  'UNKNOWN_ERROR': {
    message: 'An unexpected error occurred.',
    suggestion: 'Please try again. If the problem persists, contact our support team.',
    actionable: true
  }
};

/**
 * Get user-friendly error message from error code
 */
export function getErrorMessage(errorCode: string): ErrorMessage {
  return ERROR_MESSAGES[errorCode] || ERROR_MESSAGES['UNKNOWN_ERROR'];
}

/**
 * Get user-friendly error message with fallback to generic message
 */
export function getErrorMessageText(errorCode?: string, fallback?: string): string {
  if (!errorCode) {
    return fallback || ERROR_MESSAGES['UNKNOWN_ERROR'].message;
  }
  
  const errorMsg = getErrorMessage(errorCode);
  return errorMsg.message;
}

/**
 * Get actionable suggestion for error code
 */
export function getErrorSuggestion(errorCode?: string): string | undefined {
  if (!errorCode) {
    return ERROR_MESSAGES['UNKNOWN_ERROR'].suggestion;
  }
  
  const errorMsg = getErrorMessage(errorCode);
  return errorMsg.suggestion;
}

/**
 * Check if error has actionable suggestions for the user
 */
export function isErrorActionable(errorCode?: string): boolean {
  if (!errorCode) {
    return ERROR_MESSAGES['UNKNOWN_ERROR'].actionable || false;
  }
  
  const errorMsg = getErrorMessage(errorCode);
  return errorMsg.actionable || false;
}

/**
 * Enhanced version of the existing getApiErrorMessage function
 * with support for backend error codes
 */
export function getEnhancedApiErrorMessage(
  error: unknown, 
  defaultMessage = 'An unexpected error occurred'
): { message: string; suggestion?: string; actionable: boolean } {
  // Check if it's an axios error with error_code in response
  if (error && typeof error === 'object' && 'response' in error) {
    const axiosError = error as { response?: { data?: { error_code?: string } } };
    const errorCode = axiosError.response?.data?.error_code;
    
    if (errorCode && ERROR_MESSAGES[errorCode]) {
      const errorInfo = ERROR_MESSAGES[errorCode];
      return {
        message: errorInfo.message,
        suggestion: errorInfo.suggestion,
        actionable: errorInfo.actionable || false
      };
    }
  }
  
  // Fallback to unknown error
  return {
    message: defaultMessage,
    suggestion: ERROR_MESSAGES['UNKNOWN_ERROR'].suggestion,
    actionable: true
  };
}