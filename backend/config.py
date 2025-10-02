import os
from urllib.parse import urlparse, urlunparse
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY") or os.urandom(24)
    
    # JWT Configuration
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES_HOURS', '1')))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES_DAYS', '30')))
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    
    # Google OAuth 2.0
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    
    # Rate Limiting
    RATELIMIT_STORAGE_URI = os.getenv('REDIS_URL', 'memory://')
    RATELIMIT_DEFAULT = os.getenv('RATELIMIT_DEFAULT', '100 per hour')
    RATELIMIT_ENABLED = os.getenv('RATELIMIT_ENABLED', 'True').lower() == 'true'
    
    # File Upload
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_FILE_SIZE', 50 * 1024 * 1024))  # 50MB default
    ALLOWED_EXTENSIONS = {'pdf'}
    
    # CORS
    _origins = [o.strip() for o in os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',') if o.strip()]

    # Auto-include www/apex variants of configured origins to avoid CORS mismatches
    def _with_www_variants(origin: str) -> list[str]:
        try:
            p = urlparse(origin)
            if not p.scheme or not p.netloc:
                return [origin]
            host = p.netloc
            variants = set([origin])
            if host.startswith('www.'):
                apex = host[4:]
                variants.add(urlunparse((p.scheme, apex, p.path, '', '', '')))
            else:
                variants.add(urlunparse((p.scheme, 'www.' + host, p.path, '', '', '')))
            return list(variants)
        except Exception:
            return [origin]

    _expanded = []
    for o in _origins:
        _expanded.extend(_with_www_variants(o))

    CORS_ORIGINS = list(dict.fromkeys(_expanded))  # dedupe, preserve order
    CORS_SUPPORTS_CREDENTIALS = True
    
    # Gemini API
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
    GEMINI_MAX_RETRIES = int(os.getenv('GEMINI_MAX_RETRIES', '3'))
    GEMINI_RETRY_DELAY = int(os.getenv('GEMINI_RETRY_DELAY', '1'))
    
    # OpenAI API
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MAX_RETRIES = int(os.getenv('OPENAI_MAX_RETRIES', '3'))
    OPENAI_TIMEOUT = int(os.getenv('OPENAI_TIMEOUT', '60'))
    
    # Google APIs
    CLIENT_SECRETS_FILE = os.getenv('CLIENT_SECRETS_FILE', os.path.join(basedir, 'client_secret.json'))
    SCOPES = os.getenv(
        'GOOGLE_SCOPES',
        'https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive.file'
    ).split(',')
    TOKEN_FILE = os.getenv('TOKEN_FILE', os.path.join(basedir, 'token.json'))
    
    # Database
    # Handle both postgres:// and postgresql:// URLs (Heroku/Supabase compatibility)
    database_url = os.getenv('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app.db')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    # Ensure SSL for Supabase connections if not explicitly provided
    # Supabase requires SSL; add "sslmode=require" when missing.
    if database_url.startswith('postgresql://') and 'supabase' in database_url and 'sslmode=' not in database_url:
        sep = '&' if '?' in database_url else '?'
        database_url = f"{database_url}{sep}sslmode=require"

    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', os.path.join(basedir, 'logs', 'app.log'))