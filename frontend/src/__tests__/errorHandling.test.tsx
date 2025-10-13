/**
 * Test file for user-friendly error messages functionality
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { 
  getErrorMessage, 
  getErrorMessageText, 
  getErrorSuggestion, 
  isErrorActionable,
  getEnhancedApiErrorMessage 
} from '@/lib/errorMessages';
import ProcessingStatus from '@/components/ProcessingStatus';

describe('Error Messages', () => {
  describe('getErrorMessage', () => {
    it('should return correct error message for known error codes', () => {
      const errorInfo = getErrorMessage('INVALID_PDF');
      expect(errorInfo.message).toBe('This PDF appears corrupted or invalid.');
      expect(errorInfo.suggestion).toContain('Please try another PDF file');
      expect(errorInfo.actionable).toBe(true);
    });

    it('should return unknown error for unrecognized error codes', () => {
      const errorInfo = getErrorMessage('UNKNOWN_CODE');
      expect(errorInfo.message).toBe('An unexpected error occurred.');
      expect(errorInfo.suggestion).toContain('Please try again');
      expect(errorInfo.actionable).toBe(true);
    });
  });

  describe('getErrorMessageText', () => {
    it('should return message text for valid error code', () => {
      const message = getErrorMessageText('RATE_LIMIT_EXCEEDED');
      expect(message).toBe('Processing limit reached.');
    });

    it('should return fallback message for invalid error code', () => {
      const message = getErrorMessageText(undefined, 'Custom fallback');
      expect(message).toBe('Custom fallback');
    });
  });

  describe('getErrorSuggestion', () => {
    it('should return suggestion for error with actionable advice', () => {
      const suggestion = getErrorSuggestion('INSUFFICIENT_CREDITS');
      expect(suggestion).toContain('Please purchase more credits');
    });

    it('should return undefined for error codes without suggestions', () => {
      const suggestion = getErrorSuggestion('UNKNOWN_CODE_NO_SUGGESTION');
      expect(suggestion).toBeDefined(); // Should get unknown error suggestion
    });
  });

  describe('isErrorActionable', () => {
    it('should return true for actionable errors', () => {
      expect(isErrorActionable('INVALID_PDF')).toBe(true);
      expect(isErrorActionable('RATE_LIMIT_EXCEEDED')).toBe(true);
    });

    it('should return false for non-actionable errors', () => {
      expect(isErrorActionable('SERVER_ERROR')).toBe(false);
      expect(isErrorActionable('SERVICE_UNAVAILABLE')).toBe(false);
    });
  });

  describe('getEnhancedApiErrorMessage', () => {
    it('should handle axios error with error_code', () => {
      const mockError = {
        response: {
          data: {
            error_code: 'GEMINI_API_ERROR',
            error_message: 'AI service unavailable'
          }
        }
      };

      const result = getEnhancedApiErrorMessage(mockError);
      expect(result.message).toBe('The AI service is temporarily unavailable.');
      expect(result.suggestion).toContain('Please try again in a few minutes');
      expect(result.actionable).toBe(true);
    });

    it('should handle error without error_code', () => {
      const mockError = new Error('Generic error');
      const result = getEnhancedApiErrorMessage(mockError, 'Custom default');
      expect(result.message).toBe('Custom default');
      expect(result.actionable).toBe(true);
    });
  });
});

describe('ProcessingStatus Component', () => {
  it('should display error message with suggestion for failed status', () => {
    render(
      <ProcessingStatus
        status="failed"
        errorCode="INVALID_PDF"
        fileName="test.pdf"
        onRetry={() => {}}
        onReset={() => {}}
      />
    );

    expect(screen.getByText('Processing Failed')).toBeInTheDocument();
    expect(screen.getByText('This PDF appears corrupted or invalid.')).toBeInTheDocument();
    expect(screen.getByText(/Please try another PDF file/)).toBeInTheDocument();
    expect(screen.getByText('Try Again')).toBeInTheDocument();
    expect(screen.getByText('Start Over')).toBeInTheDocument();
  });

  it('should display processing status with progress', () => {
    render(
      <ProcessingStatus
        status="processing"
        progress={65}
        currentStep="Normalizing sentences..."
        fileName="novel.pdf"
      />
    );

    expect(screen.getByText('Normalizing sentences...')).toBeInTheDocument();
    expect(screen.getByText('65%')).toBeInTheDocument();
    expect(screen.getByText('Processing "novel.pdf"...')).toBeInTheDocument();
  });

  it('should display completion status', () => {
    render(
      <ProcessingStatus
        status="completed"
        fileName="completed.pdf"
      />
    );

    expect(screen.getByText('Processing Complete!')).toBeInTheDocument();
    expect(screen.getByText('Successfully processed "completed.pdf"')).toBeInTheDocument();
  });

  it('should call retry function when Try Again is clicked', () => {
    const mockRetry = jest.fn();
    render(
      <ProcessingStatus
        status="failed"
        errorCode="RATE_LIMIT_EXCEEDED"
        onRetry={mockRetry}
      />
    );

    const retryButton = screen.getByText('Try Again');
    fireEvent.click(retryButton);
    expect(mockRetry).toHaveBeenCalledTimes(1);
  });

  it('should show error code chip for debugging', () => {
    render(
      <ProcessingStatus
        status="failed"
        errorCode="GEMINI_API_ERROR"
      />
    );

    expect(screen.getByText('Error Code: GEMINI_API_ERROR')).toBeInTheDocument();
  });

  it('should not show retry button for non-actionable errors', () => {
    render(
      <ProcessingStatus
        status="failed"
        errorCode="SERVER_ERROR"
        onRetry={() => {}}
      />
    );

    expect(screen.queryByText('Try Again')).not.toBeInTheDocument();
  });
});

// Integration test scenarios
describe('Error Handling Integration', () => {
  const testCases = [
    {
      scenario: 'Corrupted PDF upload',
      errorCode: 'PDF_CORRUPTED',
      expectedMessage: 'This PDF appears corrupted.',
      expectedSuggestion: 'Please try another file',
      shouldShowRetry: true
    },
    {
      scenario: 'Rate limit exceeded',
      errorCode: 'RATE_LIMIT_EXCEEDED', 
      expectedMessage: 'Processing limit reached.',
      expectedSuggestion: 'Please wait a few minutes',
      shouldShowRetry: true
    },
    {
      scenario: 'No text in PDF',
      errorCode: 'NO_TEXT',
      expectedMessage: 'This PDF contains no extractable text.',
      expectedSuggestion: 'may contain only scanned images',
      shouldShowRetry: true
    },
    {
      scenario: 'AI service error',
      errorCode: 'GEMINI_API_ERROR',
      expectedMessage: 'The AI service is temporarily unavailable.',
      expectedSuggestion: 'Please try again in a few minutes',
      shouldShowRetry: true
    },
    {
      scenario: 'Insufficient credits',
      errorCode: 'INSUFFICIENT_CREDITS',
      expectedMessage: 'Insufficient credits to process this PDF.',
      expectedSuggestion: 'Please purchase more credits',
      shouldShowRetry: true
    },
    {
      scenario: 'Google permission error',
      errorCode: 'GOOGLE_PERMISSION_ERROR',
      expectedMessage: 'Access denied to Google services.',
      expectedSuggestion: 'Please grant the necessary Google Drive',
      shouldShowRetry: true
    }
  ];

  testCases.forEach(({ scenario, errorCode, expectedMessage, expectedSuggestion, shouldShowRetry }) => {
    it(`should handle ${scenario} correctly`, () => {
      const errorInfo = getErrorMessage(errorCode);
      
      expect(errorInfo.message).toBe(expectedMessage);
      expect(errorInfo.suggestion).toContain(expectedSuggestion);
      expect(errorInfo.actionable).toBe(shouldShowRetry);

      // Test component rendering
      render(
        <ProcessingStatus
          status="failed"
          errorCode={errorCode}
          onRetry={() => {}}
        />
      );

      expect(screen.getByText(expectedMessage)).toBeInTheDocument();
      expect(screen.getByText(new RegExp(expectedSuggestion))).toBeInTheDocument();
      
      if (shouldShowRetry) {
        expect(screen.getByText('Try Again')).toBeInTheDocument();
      } else {
        expect(screen.queryByText('Try Again')).not.toBeInTheDocument();
      }
    });
  });
});