"""Error handlers for the Flask application

Battleship Phase 2.2: User-Facing Error Messages
Maps common backend error codes to helpful, user-friendly messages.
"""
from flask import jsonify
from werkzeug.exceptions import HTTPException
from marshmallow import ValidationError


# Battleship Phase 2.2: Error code to user-friendly message mapping
ERROR_MESSAGES = {
    # PDF Processing Errors
    'NO_TEXT': 'This PDF appears to contain only images or scanned pages. Please upload a PDF with extractable text.',
    'CORRUPTED_PDF': 'This PDF appears to be corrupted or in an unsupported format. Please try another file.',
    'INVALID_PDF': 'The uploaded file does not appear to be a valid PDF. Please check the file format.',
    'PDF_TOO_LARGE': 'This PDF is too large to process. Please try a smaller file or split it into multiple PDFs.',
    
    # Gemini API Errors
    'GEMINI_API_ERROR': 'The AI processing service encountered an error. Please try again in a few moments.',
    'GEMINI_TIMEOUT': 'The AI processing took too long and timed out. This PDF may be too complex. Try breaking it into smaller chunks.',
    'GEMINI_RATE_LIMIT': 'Too many requests to the AI service. Please wait a moment and try again.',
    'GEMINI_LOCAL_FALLBACK': 'AI service temporarily unavailable. We processed your PDF with a backup method.',
    
    # Job/Task Errors
    'TIMEOUT': 'Processing timed out. This PDF may be too complex or too large. Please try a smaller file.',
    'FINALIZE_TIMEOUT': 'Job finalization took too long. Some chunks may not have completed. Please check your results.',
    
    # Quality Gate Errors
    'NO_VALID_SENTENCES': 'No valid sentences could be extracted from this PDF. The content may not meet our quality standards (4-8 words, complete sentences).',
    'HIGH_REJECTION_RATE': 'Most sentences in this PDF were rejected by our quality filter. The text may be too fragmented or not suitable for processing.',
    
    # Credit System Errors
    'INSUFFICIENT_CREDITS': 'You do not have enough credits to process this PDF. Please add more credits to continue.',
    'CREDIT_RESERVATION_FAILED': 'Unable to reserve credits for this job. Please try again.',
    
    # Google Services Errors
    'SHEETS_ACCESS_DENIED': 'Unable to access Google Sheets. Please re-authorize the application.',
    'SHEETS_QUOTA_EXCEEDED': 'Google Sheets API quota exceeded. Please try again later.',
    'DRIVE_ACCESS_DENIED': 'Unable to access Google Drive. Please re-authorize the application.',
}


def get_user_friendly_error(error_code: str, default_message: str = None) -> str:
    """Get user-friendly error message for error code (Battleship Phase 2.2).
    
    Args:
        error_code: Internal error code (e.g., 'NO_TEXT', 'GEMINI_TIMEOUT')
        default_message: Fallback message if code not found
        
    Returns:
        User-friendly error message
    """
    return ERROR_MESSAGES.get(error_code, default_message or 'An error occurred. Please try again.')


def register_error_handlers(app):
    """Register error handlers for the Flask application (Battleship Phase 2.2)"""
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        """Handle HTTP exceptions (4xx, 5xx errors)"""
        # Check if this is a known error with a better message
        error_message = e.description or e.name
        
        response = {
            "error": error_message,
        }
        if app.debug:
            response["code"] = e.code
            response["name"] = e.name
        return jsonify(response), e.code
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        """Handle Marshmallow validation errors"""
        return jsonify({
            "error": "Invalid request data. Please check your input and try again.",
            "details": e.messages
        }), 400
    
    @app.errorhandler(413)
    def handle_file_too_large(e):
        """Handle file upload too large error (Battleship Phase 2.2)"""
        return jsonify({
            "error": "File size exceeds maximum allowed (50MB). Please try a smaller file or split your PDF.",
            "error_code": "FILE_TOO_LARGE"
        }), 413
    
    @app.errorhandler(Exception)
    def handle_generic_exception(e):
        """Handle all other exceptions (Battleship Phase 2.2)"""
        app.logger.exception('Unhandled exception occurred')
        
        # Check if exception has an error_code attribute (custom exceptions)
        error_code = getattr(e, 'error_code', None)
        if error_code:
            friendly_message = get_user_friendly_error(error_code, str(e))
        else:
            friendly_message = "An internal error occurred. Please try again or contact support if the problem persists."
        
        return jsonify({
            "error": friendly_message if not app.debug else str(e),
            "error_code": error_code
        }), 500