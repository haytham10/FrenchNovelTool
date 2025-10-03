"""Application-wide constants"""

# Default configuration values
DEFAULT_SENTENCE_LENGTH_LIMIT = 8
DEFAULT_MAX_FILE_SIZE_MB = 50

# Rate limiting defaults
DEFAULT_RATE_LIMIT = "100 per hour"
PROCESS_PDF_RATE_LIMIT = "10 per hour"
EXPORT_SHEET_RATE_LIMIT = "20 per hour"

# Validation limits
MIN_SENTENCE_LENGTH_LIMIT = 3
MAX_SENTENCE_LENGTH_LIMIT = 50
MAX_SENTENCES_PER_REQUEST = 10000
MAX_SENTENCE_LENGTH = 5000
MAX_SHEET_NAME_LENGTH = 255

# API versioning
API_VERSION = "1.0.0"
API_SERVICE_NAME = "French Novel Tool API"

# File upload
ALLOWED_FILE_EXTENSIONS = {'pdf'}

# Gemini API
DEFAULT_GEMINI_MODEL = 'gemini-2.5-flash'
DEFAULT_GEMINI_MAX_RETRIES = 3
DEFAULT_GEMINI_RETRY_DELAY = 1

# Logging
DEFAULT_LOG_LEVEL = 'INFO'
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 10

# HTTP Status Codes
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_UNPROCESSABLE_ENTITY = 422
HTTP_INTERNAL_SERVER_ERROR = 500

# Error Codes
ERROR_INVALID_PDF = 'INVALID_PDF'
ERROR_PROCESSING = 'PROCESSING_ERROR'
ERROR_GEMINI_API = 'GEMINI_API_ERROR'
ERROR_GEMINI_RESPONSE = 'GEMINI_RESPONSE_ERROR'
ERROR_RATE_LIMIT = 'RATE_LIMIT_EXCEEDED'
ERROR_QUOTA_EXCEEDED = 'QUOTA_EXCEEDED'
ERROR_INSUFFICIENT_CREDITS = 'INSUFFICIENT_CREDITS'
ERROR_JOB_NOT_FOUND = 'JOB_NOT_FOUND'
ERROR_INVALID_JOB_STATUS = 'INVALID_JOB_STATUS'

# Processing Steps
STEP_UPLOAD = 'upload'
STEP_EXTRACT = 'extract'
STEP_ANALYZE = 'analyze'
STEP_NORMALIZE = 'normalize'
STEP_EXPORT = 'export'

# Job Status
JOB_STATUS_PENDING = 'pending'
JOB_STATUS_PROCESSING = 'processing'
JOB_STATUS_COMPLETED = 'completed'
JOB_STATUS_FAILED = 'failed'
JOB_STATUS_CANCELLED = 'cancelled'

# Credit Ledger Reasons
CREDIT_REASON_MONTHLY_GRANT = 'monthly_grant'
CREDIT_REASON_JOB_RESERVE = 'job_reserve'
CREDIT_REASON_JOB_FINAL = 'job_final'
CREDIT_REASON_JOB_REFUND = 'job_refund'
CREDIT_REASON_ADMIN_ADJUSTMENT = 'admin_adjustment'

# Pricing Configuration (v1)
PRICING_VERSION = 'v1.0'
MONTHLY_CREDIT_GRANT = 10000  # Default credits granted per month

# Model pricing: credits per 1,000 tokens
# Based on Gemini API pricing and mapped to user-facing model preferences
MODEL_PRICING = {
    'gemini-2.5-flash': 1,      # balanced - fastest, cheapest
    'gemini-2.5-flash-lite': 1, # speed - ultra-fast, experimental
    'gemini-2.5-pro': 5,        # quality - best quality, most expensive
}

# Map user-facing model preferences to actual Gemini model names
MODEL_PREFERENCE_MAP = {
    'balanced': 'gemini-2.5-flash',
    'speed': 'gemini-2.5-flash-lite',
    'quality': 'gemini-2.5-pro'
}

# Token estimation
TOKEN_ESTIMATION_CHARS_PER_TOKEN = 4  # Heuristic: 1 token ≈ 4 characters
TOKEN_ESTIMATION_SAFETY_BUFFER = 1.10  # Add 10% buffer to estimates

# Credit limits
CREDIT_OVERDRAFT_LIMIT = -100  # Allow small negative balance to handle overruns
MIN_CREDITS_FOR_JOB = 1  # Minimum credits required to start a job

# Chunking configuration for large PDFs
CHUNK_THRESHOLD_PAGES = 50  # PDFs with more than 50 pages will be chunked
DEFAULT_CHUNK_SIZE_PAGES = 25  # Process 25 pages per chunk
MAX_CHUNK_SIZE_PAGES = 50  # Maximum pages per chunk
MIN_CHUNK_SIZE_PAGES = 10  # Minimum pages per chunk

# Job Status (extended for async processing)
JOB_STATUS_QUEUED = 'queued'  # Job is queued for processing

