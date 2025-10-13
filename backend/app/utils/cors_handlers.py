"""
Enhanced CORS handling for development environments
"""
from flask import request, jsonify, current_app
from functools import wraps


def cors_preflight(f):
    """
    Decorator to handle OPTIONS preflight requests with proper CORS headers.
    Use this on routes that need explicit CORS handling.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == "OPTIONS":
            response = jsonify({})
            response.status_code = 204
            return response
        return f(*args, **kwargs)

    return decorated_function


def add_cors_headers(response):
    """
    Add CORS headers to a response object.
    This can be used in an after_request handler.

    NOTE: This function is kept for backwards compatibility but should NOT be used
    when Flask-CORS is already configured, as it will cause duplicate headers.
    """
    # Disabled to prevent duplicate CORS headers when Flask-CORS is active
    return response


def setup_cors_handling(app):
    """
    Configure enhanced CORS handling for a Flask app.

    NOTE: This function is now a no-op since Flask-CORS extension handles
    all CORS headers. Kept for backwards compatibility.
    """
    # No-op: Flask-CORS extension (configured in __init__.py) handles everything
    pass
