"""Authentication routes for user login, logout, and token management"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    jwt_required,
    create_access_token,
    create_refresh_token,
    get_jwt_identity
)
from marshmallow import ValidationError
from app.services.auth_service import AuthService
from app.schemas import GoogleAuthSchema
from app.models import User

auth_bp = Blueprint('auth', __name__)
auth_service = AuthService()
google_auth_schema = GoogleAuthSchema()


@auth_bp.route('/google', methods=['POST', 'OPTIONS'])
def google_login():
    """
    Authenticates user with Google OAuth.
    Supports both ID token (legacy) and authorization code (recommended) flows.
    
    Request body should contain either:
    - { "token": "<id_token>" } for ID token flow (legacy, no Sheets/Drive access)
    - { "code": "<auth_code>" } for OAuth flow (recommended, includes Sheets/Drive access)
    """
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Invalid request data'}), 400
        
        # Check which flow to use
        auth_code = data.get('code')
        id_token_str = data.get('token')
        
        if auth_code:
            # OAuth flow - exchange code for tokens
            try:
                token_data = auth_service.exchange_code_for_tokens(auth_code)
                google_user_info = token_data['user_info']
                oauth_tokens = {
                    'access_token': token_data['access_token'],
                    'refresh_token': token_data['refresh_token'],
                    'expiry': token_data['expiry']
                }
            except Exception as e:
                current_app.logger.error(f"OAuth code exchange failed: {e}")
                return jsonify({'error': 'Failed to authenticate with Google'}), 401
        
        elif id_token_str:
            # ID token flow (legacy)
            try:
                google_user_info = auth_service.verify_google_token(id_token_str)
                oauth_tokens = None  # No OAuth tokens with ID token flow
                current_app.logger.warning(f"User {google_user_info.get('email')} logged in with ID token (no Sheets/Drive access)")
            except Exception as e:
                current_app.logger.error(f"ID token verification failed: {e}")
                return jsonify({'error': 'Invalid authentication token'}), 401
        
        else:
            return jsonify({'error': 'Either code or token must be provided'}), 400
        
        # Get or create user with OAuth tokens
        user = auth_service.get_or_create_user(google_user_info, oauth_tokens)
        
        if not user or not user.is_active:
            return jsonify({'error': 'User account is inactive or could not be created'}), 401

        # Create JWT tokens (identity must be a string)
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))

        response = jsonify({
            'message': 'Login successful',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.to_dict(),
            'has_sheets_access': bool(user.google_access_token)
        })
        
        current_app.logger.info(f"User {user.email} logged in via Google.")
        return response, 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 401
    except Exception as e:
        current_app.logger.exception('Authentication failed')
        return jsonify({'error': 'Authentication failed'}), 500


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Refreshes an expired access token using a valid refresh token.
    """
    try:
        user_id = get_jwt_identity()  # This will be a string now
        access_token = create_access_token(identity=user_id)  # Keep as string
        
        return jsonify({
            'access_token': access_token
        }), 200
        
    except Exception as e:
        current_app.logger.exception('Token refresh failed')
        return jsonify({'error': 'Token refresh failed'}), 500


@auth_bp.route('/me', methods=['GET', 'OPTIONS'])
@jwt_required()
def get_current_user():
    """
    Returns information about the currently authenticated user.
    """
    try:
        user_id = get_jwt_identity()  # This will be a string
        user = User.query.get(int(user_id))  # Convert to int for database query

        if not user or not user.is_active:
            return jsonify({'error': 'User not found or inactive'}), 404

        return jsonify(user.to_dict()), 200
        
    except Exception as e:
        current_app.logger.exception('Failed to get user info')
        return jsonify({'error': 'Failed to get user information'}), 500


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logout current user.
    
    Note: With JWT, actual logout happens client-side by removing tokens.
    This endpoint is for logging purposes and can be extended for token blacklisting.
    """
    try:
        user_id = get_jwt_identity()
        current_app.logger.info(f'User {user_id} logged out')
        
        return jsonify({'message': 'Logged out successfully'}), 200
        
    except Exception as e:
        current_app.logger.exception('Logout failed')
        return jsonify({'error': 'Logout failed'}), 500


