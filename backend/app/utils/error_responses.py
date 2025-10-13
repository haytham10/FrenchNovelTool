"""
Error response utilities for consistent API error handling
"""

from flask import jsonify
from typing import Optional, Dict, Any, Tuple
from app.constants import ERROR_UNKNOWN


def create_error_response(
    error_code: str,
    message: str,
    status_code: int = 400,
    details: Optional[Dict[str, Any]] = None
) -> Tuple[Dict[str, Any], int]:
    """
    Create a standardized error response with error code for frontend mapping.
    
    Args:
        error_code: Backend error code (from constants.py)
        message: Human-readable error message 
        status_code: HTTP status code
        details: Optional additional error details
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    response = {
        'error': message,
        'error_code': error_code,
        'error_message': message,  # Alias for backwards compatibility
        'success': False
    }
    
    if details:
        response['details'] = details
        
    return response, status_code


def create_error_json_response(
    error_code: str,
    message: str,
    status_code: int = 400,
    details: Optional[Dict[str, Any]] = None
):
    """
    Create a Flask JSON error response with error code.
    
    Args:
        error_code: Backend error code (from constants.py)
        message: Human-readable error message
        status_code: HTTP status code
        details: Optional additional error details
        
    Returns:
        Flask JSON response
    """
    response_data, status = create_error_response(error_code, message, status_code, details)
    return jsonify(response_data), status


def handle_validation_error(error_message: str, field: Optional[str] = None):
    """Handle validation errors with consistent formatting."""
    from app.constants import ERROR_INVALID_SETTINGS
    
    details = {'field': field} if field else None
    return create_error_json_response(
        ERROR_INVALID_SETTINGS,
        error_message,
        400,
        details
    )


def handle_file_error(error_code: str, message: str):
    """Handle file upload/processing errors."""
    return create_error_json_response(error_code, message, 400)


def handle_processing_error(error_code: str, message: str, details: Optional[Dict[str, Any]] = None):
    """Handle PDF processing errors."""
    return create_error_json_response(error_code, message, 500, details)


def handle_auth_error(error_code: str, message: str):
    """Handle authentication/authorization errors."""
    return create_error_json_response(error_code, message, 401)


def handle_rate_limit_error(message: str = "Rate limit exceeded"):
    """Handle rate limiting errors."""
    from app.constants import ERROR_RATE_LIMIT
    return create_error_json_response(ERROR_RATE_LIMIT, message, 429)


def handle_credit_error(message: str = "Insufficient credits"):
    """Handle credit/quota errors."""
    from app.constants import ERROR_INSUFFICIENT_CREDITS
    return create_error_json_response(ERROR_INSUFFICIENT_CREDITS, message, 402)


def handle_google_error(error_code: str, message: str):
    """Handle Google API errors."""
    return create_error_json_response(error_code, message, 503)


def handle_unknown_error(message: str = "An unexpected error occurred"):
    """Handle unknown/generic errors."""
    return create_error_json_response(ERROR_UNKNOWN, message, 500)