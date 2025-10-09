"""Authentication service for Google OAuth 2.0"""
from google.oauth2 import id_token
from google.auth.transport import requests
from google.oauth2.credentials import Credentials
from flask import current_app
from app import db
from app.models import User, UserSettings
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build


class AuthService:
    """Service for handling authentication operations"""
    
    def verify_google_token(self, token):
        """
        Verify Google OAuth 2.0 token and return user info.
        
        Args:
            token: Google ID token from frontend
            
        Returns:
            dict: User information from Google
            
        Raises:
            ValueError: If token is invalid
        """
        try:
            # Verify the token
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                current_app.config['GOOGLE_CLIENT_ID']
            )
            
            # Verify issuer
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer')
            
            return {
                'google_id': idinfo['sub'],
                'email': idinfo['email'],
                'name': idinfo.get('name', ''),
                'picture': idinfo.get('picture', '')
            }
        except ValueError as e:
            current_app.logger.error(f'Invalid Google token: {str(e)}')
            raise ValueError('Invalid authentication token')
    
    def exchange_code_for_tokens(self, code):
        """
        Exchange authorization code for OAuth tokens.
        
        Args:
            code: Authorization code from frontend
            
        Returns:
            dict: OAuth tokens including access_token, refresh_token, and expiry
            
        Raises:
            ValueError: If code exchange fails
        """
        try:
            from google_auth_oauthlib.flow import Flow
            
            # Create flow instance
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": current_app.config['GOOGLE_CLIENT_ID'],
                        "client_secret": current_app.config.get('GOOGLE_CLIENT_SECRET', ''),
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                },
                scopes=[
                    'openid',
                    'https://www.googleapis.com/auth/userinfo.email',
                    'https://www.googleapis.com/auth/userinfo.profile',
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive.file',
                ],
                redirect_uri='postmessage'  # For popup flow
            )
            
            # Exchange code for tokens
            flow.fetch_token(code=code)
            credentials = flow.credentials

            # Ensure required scopes were actually granted by the user
            required_scopes = {
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive.file',
            }
            granted_scopes = set(credentials.scopes or [])
            missing = required_scopes - granted_scopes
            if missing:
                current_app.logger.warning(
                    'OAuth scopes missing after code exchange: %s (granted=%s)',
                    ', '.join(sorted(missing)), ', '.join(sorted(granted_scopes))
                )
                # Inform the client to re-initiate consent with the full scopes
                raise ValueError(
                    'Insufficient permissions: additional Google Drive access is required. '
                    'Please sign in again and accept Drive permissions (drive.readonly and drive.file).'
                )
            
            # Get user info from ID token
            idinfo = id_token.verify_oauth2_token(
                credentials.id_token,
                requests.Request(),
                current_app.config['GOOGLE_CLIENT_ID']
            )
            
            # Calculate expiry time
            expiry = datetime.now(timezone.utc) + timedelta(seconds=credentials.expiry.timestamp() - datetime.now(timezone.utc).timestamp())
            
            return {
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'expiry': expiry,
                'user_info': {
                    'google_id': idinfo['sub'],
                    'email': idinfo['email'],
                    'name': idinfo.get('name', ''),
                    'picture': idinfo.get('picture', '')
                }
            }
        except Exception as e:
            current_app.logger.error(f'Failed to exchange code for tokens: {str(e)}')
            raise ValueError('Failed to authenticate with Google')
    
    def get_or_create_user(self, google_user_info, oauth_tokens=None):
        """
        Get existing user or create new one from Google user info.
        
        Args:
            google_user_info: Dictionary with user info from Google
            oauth_tokens: Optional dictionary with OAuth tokens (access_token, refresh_token, expiry)
            
        Returns:
            User: User model instance
        """
        user = User.query.filter_by(google_id=google_user_info['google_id']).first()
        
        if user:
            # Update existing user info
            user.email = google_user_info['email']
            user.name = google_user_info['name']
            user.picture = google_user_info['picture']
            user.last_login = datetime.now(timezone.utc)
            
            # Update OAuth tokens if provided
            if oauth_tokens:
                user.google_access_token = oauth_tokens.get('access_token')
                user.google_refresh_token = oauth_tokens.get('refresh_token')
                user.google_token_expiry = oauth_tokens.get('expiry')
        else:
            # Create new user
            user = User(
                google_id=google_user_info['google_id'],
                email=google_user_info['email'],
                name=google_user_info['name'],
                picture=google_user_info['picture']
            )
            
            # Set OAuth tokens if provided
            if oauth_tokens:
                user.google_access_token = oauth_tokens.get('access_token')
                user.google_refresh_token = oauth_tokens.get('refresh_token')
                user.google_token_expiry = oauth_tokens.get('expiry')
            
            db.session.add(user)
            db.session.flush()  # Get user ID
            
            # Create default settings for new user
            settings = UserSettings(user_id=user.id, sentence_length_limit=8)
            db.session.add(settings)
        
        db.session.commit()
        return user
    
    def refresh_user_token(self, user):
        """
        Refresh the user's OAuth access token using refresh token.
        
        Args:
            user: User model instance
            
        Returns:
            str: New access token
            
        Raises:
            ValueError: If refresh fails
        """
        if not user.google_refresh_token:
            raise ValueError('No refresh token available')
        
        try:
            credentials = Credentials(
                token=user.google_access_token,
                refresh_token=user.google_refresh_token,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=current_app.config['GOOGLE_CLIENT_ID'],
                client_secret=current_app.config.get('GOOGLE_CLIENT_SECRET', '')
            )
            
            # Refresh the token
            credentials.refresh(requests.Request())
            
            # Update user's tokens
            user.google_access_token = credentials.token
            if credentials.expiry:
                user.google_token_expiry = credentials.expiry
            
            db.session.commit()
            
            return credentials.token
        except Exception as e:
            current_app.logger.error(f'Failed to refresh token: {str(e)}')
            raise ValueError('Failed to refresh authentication token')
    
    def get_user_credentials(self, user):
        """
        Get valid Google credentials for a user, refreshing if necessary.
        
        Args:
            user: User model instance
            
        Returns:
            Credentials: Google OAuth2 credentials
            
        Raises:
            ValueError: If user has no tokens or refresh fails
        """
        if not user.google_access_token:
            raise ValueError('User has not authorized Google access')
        
        # Check if token is expired
        if user.google_token_expiry and user.google_token_expiry < datetime.now(timezone.utc):
            current_app.logger.info(f'Token expired for user {user.id}, refreshing...')
            self.refresh_user_token(user)
        
        credentials = Credentials(
            token=user.google_access_token,
            refresh_token=user.google_refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=current_app.config['GOOGLE_CLIENT_ID'],
            client_secret=current_app.config.get('GOOGLE_CLIENT_SECRET', '')
        )
        
        return credentials
    
    def deactivate_user(self, user_id):
        """
        Deactivate a user account.
        
        Args:
            user_id: ID of user to deactivate
            
        Returns:
            bool: True if successful
        """
        user = User.query.get(user_id)
        if user:
            user.is_active = False
            db.session.commit()
            return True
        return False

