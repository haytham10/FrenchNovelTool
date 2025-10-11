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
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000,https://www.frenchnoveltool.com,https://frenchnoveltool.com')
    CORS_SUPPORTS_CREDENTIALS = True
    
    # Gemini API
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
    GEMINI_MAX_RETRIES = int(os.getenv('GEMINI_MAX_RETRIES', '3'))
    GEMINI_RETRY_DELAY = int(os.getenv('GEMINI_RETRY_DELAY', '1'))
    
    # Google APIs
    CLIENT_SECRETS_FILE = os.getenv('CLIENT_SECRETS_FILE', os.path.join(basedir, 'client_secret.json'))
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "openid",
        "https://www.googleapis.com/auth/drive.file"
    ]
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
    
    # Database Connection Pool Configuration (critical for Supabase + Railway deployment)
    # Optimized for 8GB RAM / 8 vCPU with high concurrency workloads
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.getenv('DB_POOL_SIZE', '20')),
        'pool_pre_ping': True,
        'pool_recycle': int(os.getenv('DB_POOL_RECYCLE', '1800')),
        'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', '10')),
    }

    if SQLALCHEMY_DATABASE_URI.startswith('postgresql'):
        SQLALCHEMY_ENGINE_OPTIONS['connect_args'] = {
            'connect_timeout': int(os.getenv('DB_CONNECT_TIMEOUT', '15')),
            'options': '-c statement_timeout=60000'
        }
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', os.path.join(basedir, 'logs', 'app.log'))
    
    # Celery Configuration
    # Support both standard Redis and Redis with SSL (Railway/Upstash)
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Parse Redis URL and add SSL if needed for production
    if redis_url.startswith('rediss://') or (redis_url.startswith('redis://') and os.getenv('REDIS_TLS', 'false').lower() == 'true'):
        # Already using rediss:// or TLS requested
        if not redis_url.startswith('rediss://'):
            redis_url = redis_url.replace('redis://', 'rediss://', 1)
        # Add SSL cert verification settings
        redis_broker_url = redis_url + '?ssl_cert_reqs=none' if '?' not in redis_url else redis_url + '&ssl_cert_reqs=none'
        redis_backend_url = redis_url + '?ssl_cert_reqs=none' if '?' not in redis_url else redis_url + '&ssl_cert_reqs=none'
    else:
        redis_broker_url = redis_url
        redis_backend_url = redis_url
    
    CELERY_BROKER_URL = redis_broker_url
    CELERY_RESULT_BACKEND = redis_backend_url
    CELERY_TASK_IGNORE_RESULT = False  # We need results for progress tracking
    
    # Celery Task Configuration - Optimized for 8GB RAM / 8 vCPU Railway infrastructure
    CHUNK_TASK_MAX_RETRIES = int(os.getenv('CHUNK_TASK_MAX_RETRIES', '4'))  # More retries with better resources
    CHUNK_TASK_RETRY_DELAY = int(os.getenv('CHUNK_TASK_RETRY_DELAY', '3'))  # Faster retries
    CHORD_WATCHDOG_SECONDS = int(os.getenv('CHORD_WATCHDOG_SECONDS', '300'))  # 5 min - more breathing room
    CHUNK_WATCHDOG_SECONDS = int(os.getenv('CHUNK_WATCHDOG_SECONDS', '600'))  # 10 min - handle large chunks
    # If a chunk remains 'processing' longer than this, it's likely stuck
    CHUNK_STUCK_THRESHOLD_SECONDS = int(os.getenv('CHUNK_STUCK_THRESHOLD_SECONDS', '720'))  # 12 minutes
    # Finalization Configuration
    FINALIZE_MAX_RETRIES = int(os.getenv('FINALIZE_MAX_RETRIES', '10'))  # More retries for complex jobs
    FINALIZE_RETRY_DELAY = int(os.getenv('FINALIZE_RETRY_DELAY', '15'))  # Faster checks
    
    # LLM Call Timeout (prevent indefinite hangs)
    GEMINI_CALL_TIMEOUT_SECONDS = int(os.getenv('GEMINI_CALL_TIMEOUT_SECONDS', '300'))  # 5 min for large chunks

    # Stage 2: Adaptive AI Prompt System (ENABLED by default - production ready)
    # Toggle between old monolithic prompt and new three-tier adaptive system
    GEMINI_USE_ADAPTIVE_PROMPTS = os.getenv('GEMINI_USE_ADAPTIVE_PROMPTS', 'True').lower() == 'true'

    # Adaptive Prompt Configuration
    # These settings control the behavior of the three-tier prompt system
    GEMINI_PASSTHROUGH_ENABLED = os.getenv('GEMINI_PASSTHROUGH_ENABLED', 'True').lower() == 'true'  # Skip API for perfect sentences
    GEMINI_BATCH_PROCESSING_ENABLED = os.getenv('GEMINI_BATCH_PROCESSING_ENABLED', 'True').lower() == 'true'  # Batch light rewrites
    
    # Stage 3: Post-Processing Quality Gate
    # Validation settings for sentence quality control
    VALIDATION_ENABLED = os.getenv('VALIDATION_ENABLED', 'True').lower() == 'true'
    VALIDATION_DISCARD_FAILURES = os.getenv('VALIDATION_DISCARD_FAILURES', 'True').lower() == 'true'  # Critical for quality
    VALIDATION_MIN_WORDS = int(os.getenv('VALIDATION_MIN_WORDS', '4'))
    VALIDATION_MAX_WORDS = int(os.getenv('VALIDATION_MAX_WORDS', '8'))
    VALIDATION_REQUIRE_VERB = os.getenv('VALIDATION_REQUIRE_VERB', 'True').lower() == 'true'
    VALIDATION_LOG_FAILURES = os.getenv('VALIDATION_LOG_FAILURES', 'True').lower() == 'true'
    VALIDATION_LOG_SAMPLE_SIZE = int(os.getenv('VALIDATION_LOG_SAMPLE_SIZE', '20'))