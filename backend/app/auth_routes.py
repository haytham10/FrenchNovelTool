"""Authentication routes for user login, logout, and token management"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    jwt_required,
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    get_jwt
)
from marshmallow import ValidationError
from app.services.auth_service import AuthService
from app.schemas import GoogleAuthSchema
from app.models import User

auth_bp = Blueprint('auth', __name__)
auth_service = AuthService()
google_auth_schema = GoogleAuthSchema()


@auth_bp.route('/google', methods=['POST'])
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
        
        # Get JWT ID (jti) from the refresh token for session tracking
        from flask_jwt_extended import decode_token
        decoded_refresh = decode_token(refresh_token)
        refresh_token_jti = decoded_refresh['jti']
        
        # Create server-side session
        user_agent = request.headers.get('User-Agent')
        ip_address = request.remote_addr
        session = auth_service.create_session(
            user_id=user.id,
            refresh_token_jti=refresh_token_jti,
            user_agent=user_agent,
            ip_address=ip_address
        )

        response = jsonify({
            'message': 'Login successful',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'session_token': session.session_token,
            'user': user.to_dict(),
            'has_sheets_access': bool(user.google_access_token)
        })
        
        current_app.logger.info(f"User {user.email} logged in via Google with session {session.id}.")
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
    Validates the associated server-side session.
    """
    try:
        user_id = get_jwt_identity()  # This will be a string now
        jwt_data = get_jwt()
        refresh_token_jti = jwt_data.get('jti')
        
        # Validate the session associated with this refresh token
        session = auth_service.validate_session_by_jti(refresh_token_jti)
        if not session:
            current_app.logger.warning(f"Invalid or expired session for user {user_id}")
            return jsonify({'error': 'Session expired. Please log in again.'}), 401
        
        # Check that the session belongs to this user
        if session.user_id != int(user_id):
            current_app.logger.error(f"Session user mismatch: session.user_id={session.user_id}, jwt user_id={user_id}")
            return jsonify({'error': 'Invalid session'}), 401
        
        # Create new tokens
        access_token = create_access_token(identity=user_id)  # Keep as string
        refresh_token = create_refresh_token(identity=user_id)  # Generate new refresh token
        
        # Update session with new refresh token JTI
        from flask_jwt_extended import decode_token
        decoded_refresh = decode_token(refresh_token)
        new_refresh_token_jti = decoded_refresh['jti']
        session.refresh_token_jti = new_refresh_token_jti
        session.update_activity()
        from app import db
        db.session.commit()

        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'session_token': session.session_token
        }), 200
        
    except Exception as e:
        current_app.logger.exception('Token refresh failed')
        return jsonify({'error': 'Token refresh failed'}), 500


@auth_bp.route('/me', methods=['GET'])
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
    Logout current user by revoking their session.
    
    Note: With JWT, actual logout happens client-side by removing tokens.
    This endpoint revokes the server-side session for security.
    """
    try:
        user_id = get_jwt_identity()
        
        # Get session token from request if provided
        data = request.json or {}
        session_token = data.get('session_token')
        
        if session_token:
            auth_service.revoke_session(session_token)
            current_app.logger.info(f'User {user_id} logged out (session revoked)')
        else:
            current_app.logger.info(f'User {user_id} logged out (no session token provided)')
        
        return jsonify({'message': 'Logged out successfully'}), 200
        
    except Exception as e:
        current_app.logger.exception('Logout failed')
        return jsonify({'error': 'Logout failed'}), 500


@auth_bp.route('/sessions', methods=['GET'])
@jwt_required()
def get_user_sessions():
    """
    Get all active sessions for the current user.
    """
    try:
        user_id = int(get_jwt_identity())
        sessions = auth_service.get_user_sessions(user_id)
        
        return jsonify({
            'sessions': [session.to_dict() for session in sessions]
        }), 200
        
    except Exception as e:
        current_app.logger.exception('Failed to get user sessions')
        return jsonify({'error': 'Failed to retrieve sessions'}), 500


@auth_bp.route('/sessions/revoke', methods=['POST'])
@jwt_required()
def revoke_sessions():
    """
    Revoke all sessions for the current user (except the current one).
    Useful for "logout from all devices" functionality.
    """
    try:
        user_id = int(get_jwt_identity())
        data = request.json or {}
        current_session_token = data.get('current_session_token')
        
        # Get the current session ID if token provided
        current_session_id = None
        if current_session_token:
            current_session = auth_service.validate_session(current_session_token)
            if current_session:
                current_session_id = current_session.id
        
        count = auth_service.revoke_user_sessions(user_id, except_session_id=current_session_id)
        
        return jsonify({
            'message': f'Revoked {count} session(s)',
            'revoked_count': count
        }), 200
        
    except Exception as e:
        current_app.logger.exception('Failed to revoke sessions')
        return jsonify({'error': 'Failed to revoke sessions'}), 500
        return jsonify({'error': 'Logout failed'}), 500


