"""Authentication service for Google OAuth 2.0"""
from google.oauth2 import id_token
from google.auth.transport import requests
from google.oauth2.credentials import Credentials
from flask import current_app
from app import db
from app.models import User, UserSettings, UserSession
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
            
            # Calculate expiry time (ensure timezone-aware UTC)
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
                # Normalize expiry to timezone-aware UTC if possible
                expiry_val = oauth_tokens.get('expiry')
                if expiry_val:
                    try:
                        if isinstance(expiry_val, str):
                            # Try to parse ISO format
                            parsed = datetime.fromisoformat(expiry_val)
                            expiry_val = parsed
                    except Exception:
                        pass

                    if isinstance(expiry_val, datetime) and expiry_val.tzinfo is None:
                        expiry_val = expiry_val.replace(tzinfo=timezone.utc)

                    user.google_token_expiry = expiry_val
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
                expiry_val = oauth_tokens.get('expiry')
                if expiry_val:
                    try:
                        if isinstance(expiry_val, str):
                            parsed = datetime.fromisoformat(expiry_val)
                            expiry_val = parsed
                    except Exception:
                        pass

                    if isinstance(expiry_val, datetime) and expiry_val.tzinfo is None:
                        expiry_val = expiry_val.replace(tzinfo=timezone.utc)

                    user.google_token_expiry = expiry_val
            
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
                expiry_val = credentials.expiry
                # credentials.expiry from google oauth is usually timezone-aware
                if isinstance(expiry_val, datetime) and expiry_val.tzinfo is None:
                    expiry_val = expiry_val.replace(tzinfo=timezone.utc)
                user.google_token_expiry = expiry_val
            
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
        
        # Check if token is expired (ensure stored expiry is timezone-aware)
        expiry_val = user.google_token_expiry
        if expiry_val and isinstance(expiry_val, datetime) and expiry_val.tzinfo is None:
            expiry_val = expiry_val.replace(tzinfo=timezone.utc)

        if expiry_val and expiry_val < datetime.now(timezone.utc):
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
    
    def create_session(self, user_id, refresh_token_jti, user_agent=None, ip_address=None):
        """
        Create a new server-side session for the user.
        
        Args:
            user_id: ID of the user
            refresh_token_jti: JWT ID from the refresh token
            user_agent: User agent string from request
            ip_address: IP address of the client
            
        Returns:
            UserSession: Created session object
        """
        # Calculate session expiry based on config
        session_expiry_days = current_app.config.get('SESSION_EXPIRY_DAYS', 14)
        expires_at = datetime.utcnow() + timedelta(days=session_expiry_days)
        
        # Generate secure session token
        session_token = UserSession.generate_session_token()
        
        # Create session
        session = UserSession(
            user_id=user_id,
            session_token=session_token,
            refresh_token_jti=refresh_token_jti,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=expires_at
        )
        
        db.session.add(session)
        db.session.commit()
        
        current_app.logger.info(f"Created session for user {user_id}, expires at {expires_at}")
        return session
    
    def validate_session(self, session_token):
        """
        Validate a session token and return the associated session.
        
        Args:
            session_token: Session token to validate
            
        Returns:
            UserSession or None: Valid session object or None if invalid
        """
        session = UserSession.query.filter_by(
            session_token=session_token,
            is_active=True
        ).first()
        
        if not session:
            return None
        
        # Check if session has expired
        if session.is_expired():
            current_app.logger.info(f"Session {session.id} expired")
            session.revoke()
            db.session.commit()
            return None
        
        # Update last activity
        session.update_activity()
        db.session.commit()
        
        return session
    
    def validate_session_by_jti(self, refresh_token_jti):
        """
        Validate a session by refresh token JTI.
        
        Args:
            refresh_token_jti: JWT ID from refresh token
            
        Returns:
            UserSession or None: Valid session object or None if invalid
        """
        session = UserSession.query.filter_by(
            refresh_token_jti=refresh_token_jti,
            is_active=True
        ).first()
        
        if not session:
            return None
        
        # Check if session has expired
        if session.is_expired():
            current_app.logger.info(f"Session {session.id} expired")
            session.revoke()
            db.session.commit()
            return None
        
        # Update last activity
        session.update_activity()
        db.session.commit()
        
        return session
    
    def revoke_session(self, session_token):
        """
        Revoke a session (logout).
        
        Args:
            session_token: Session token to revoke
            
        Returns:
            bool: True if successful
        """
        session = UserSession.query.filter_by(session_token=session_token).first()
        if session:
            session.revoke()
            db.session.commit()
            current_app.logger.info(f"Revoked session {session.id} for user {session.user_id}")
            return True
        return False
    
    def revoke_user_sessions(self, user_id, except_session_id=None):
        """
        Revoke all sessions for a user (except optionally one session).
        
        Args:
            user_id: ID of the user
            except_session_id: Optional session ID to exclude from revocation
            
        Returns:
            int: Number of sessions revoked
        """
        query = UserSession.query.filter_by(user_id=user_id, is_active=True)
        if except_session_id:
            query = query.filter(UserSession.id != except_session_id)
        
        sessions = query.all()
        count = 0
        for session in sessions:
            session.revoke()
            count += 1
        
        db.session.commit()
        current_app.logger.info(f"Revoked {count} sessions for user {user_id}")
        return count
    
    def cleanup_expired_sessions(self):
        """
        Clean up expired sessions from the database.
        Should be called periodically (e.g., daily via cron/celery).
        
        Returns:
            int: Number of sessions cleaned up
        """
        # Delete expired and inactive sessions
        count = UserSession.query.filter(
            db.or_(
                UserSession.expires_at < datetime.utcnow(),
                UserSession.is_active == False
            )
        ).delete()
        
        db.session.commit()
        current_app.logger.info(f"Cleaned up {count} expired/inactive sessions")
        return count
    
    def get_user_sessions(self, user_id):
        """
        Get all active sessions for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            list: List of active UserSession objects
        """
        return UserSession.query.filter_by(
            user_id=user_id,
            is_active=True
        ).filter(
            UserSession.expires_at > datetime.utcnow()
        ).order_by(UserSession.last_activity.desc()).all()


