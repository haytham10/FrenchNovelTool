"""Error handlers for the Flask application"""
from flask import jsonify
from werkzeug.exceptions import HTTPException
from marshmallow import ValidationError


def register_error_handlers(app):
    """Register error handlers for the Flask application"""
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        """Handle HTTP exceptions (4xx, 5xx errors)"""
        response = {
            "error": e.description or e.name,
        }
        if app.debug:
            response["code"] = e.code
            response["name"] = e.name
        return jsonify(response), e.code
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        """Handle Marshmallow validation errors"""
        return jsonify({
            "error": "Validation error",
            "details": e.messages
        }), 400
    
    @app.errorhandler(413)
    def handle_file_too_large(e):
        """Handle file upload too large error"""
        return jsonify({
            "error": "File size exceeds maximum allowed (50MB)"
        }), 413
    
    @app.errorhandler(Exception)
    def handle_generic_exception(e):
        """Handle all other exceptions"""
        app.logger.exception('Unhandled exception occurred')
        return jsonify({
            "error": "An internal error occurred" if not app.debug else str(e)
        }), 500