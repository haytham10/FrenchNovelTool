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
        if request.method == 'OPTIONS':
            response = jsonify({})
            response.status_code = 204
            return response
        return f(*args, **kwargs)
    return decorated_function


def add_cors_headers(response):
    """
    Add CORS headers to a response object.
    This can be used in an after_request handler.
    """
    origin = request.headers.get('Origin', '')
    allowed_origins = current_app.config.get('CORS_ORIGINS', [])
    
    # Check if origin matches any allowed origins (supporting wildcards)
    origin_allowed = False
    for allowed in allowed_origins:
        if allowed == '*' or origin == allowed:
            origin_allowed = True
            break
    
    if origin_allowed:
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Allow-Headers', 
                          'Content-Type, Authorization, X-Requested-With')
        response.headers.add('Access-Control-Allow-Methods',
                          'GET, POST, PUT, PATCH, DELETE, OPTIONS')
        
    return response


def setup_cors_handling(app):
    """
    Configure enhanced CORS handling for a Flask app.
    Adds an after_request handler to ensure all responses have proper CORS headers.
    """
    @app.after_request
    def apply_cors_headers(response):
        return add_cors_headers(response)
    
    # Globally handle OPTIONS requests
    @app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
    @app.route('/<path:path>', methods=['OPTIONS'])
    def options_handler(path):
        response = jsonify({})
        response.status_code = 204
        return response