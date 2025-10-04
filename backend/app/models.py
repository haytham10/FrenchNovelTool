from datetime import datetime
from sqlalchemy import Index
from app import db


class User(db.Model):
    """Model for user accounts"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255))
    picture = db.Column(db.String(512))
    google_id = db.Column(db.String(255), unique=True, index=True)
    google_access_token = db.Column(db.Text)  # OAuth access token for Sheets/Drive
    google_refresh_token = db.Column(db.Text)  # OAuth refresh token
    google_token_expiry = db.Column(db.DateTime)  # Token expiration time
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships
    history = db.relationship('History', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    settings = db.relationship('UserSettings', backref='user', uselist=False, cascade='all, delete-orphan')
    credit_ledger = db.relationship('CreditLedger', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    jobs = db.relationship('Job', backref='user', lazy='dynamic', cascade='all, delete-orphan', foreign_keys='Job.user_id')
    cancelled_jobs = db.relationship('Job', backref='canceller', lazy='dynamic', foreign_keys='Job.cancelled_by')
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'picture': self.picture,
            'created_at': self.created_at.isoformat() + 'Z',
            'last_login': self.last_login.isoformat() + 'Z' if self.last_login else None
        }


class History(db.Model):
    """Model for tracking PDF processing history"""
    __tablename__ = 'history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=True, index=True)  # Link to job for credit tracking
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow, nullable=False)
    original_filename = db.Column(db.String(128), index=True)
    processed_sentences_count = db.Column(db.Integer)
    spreadsheet_url = db.Column(db.String(256))
    error_message = db.Column(db.String(512))
    # P1 feature fields
    failed_step = db.Column(db.String(50))  # 'upload', 'extract', 'analyze', 'normalize', 'export'
    error_code = db.Column(db.String(50))   # 'QUOTA_EXCEEDED', 'INVALID_PDF', etc.
    error_details = db.Column(db.JSON)      # Additional error context
    processing_settings = db.Column(db.JSON)  # Store all settings for duplicate/retry

    def __repr__(self):
        return f'<History {self.original_filename} - {self.timestamp}>'

    def to_dict(self):
        return {
            'id': self.id,
            'job_id': self.job_id,
            'timestamp': self.timestamp.isoformat() + 'Z',
            'original_filename': self.original_filename,
            'processed_sentences_count': self.processed_sentences_count,
            'spreadsheet_url': self.spreadsheet_url,
            'error_message': self.error_message,
            'failed_step': self.failed_step,
            'error_code': self.error_code,
            'error_details': self.error_details,
            'settings': self.processing_settings
        }


class UserSettings(db.Model):
    """Model for storing user settings in database"""
    __tablename__ = 'user_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True, index=True)
    sentence_length_limit = db.Column(db.Integer, nullable=False, default=8)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # P1 advanced normalization fields
    gemini_model = db.Column(db.String(50), default='balanced')
    ignore_dialogue = db.Column(db.Boolean, default=False)
    preserve_formatting = db.Column(db.Boolean, default=True)
    fix_hyphenation = db.Column(db.Boolean, default=True)
    min_sentence_length = db.Column(db.Integer, default=2)
    
    def __repr__(self):
        return f'<UserSettings user_id={self.user_id} sentence_length_limit={self.sentence_length_limit}>'
    
    def to_dict(self):
        return {
            'sentence_length_limit': self.sentence_length_limit,
            'gemini_model': self.gemini_model,
            'ignore_dialogue': self.ignore_dialogue,
            'preserve_formatting': self.preserve_formatting,
            'fix_hyphenation': self.fix_hyphenation,
            'min_sentence_length': self.min_sentence_length
        }


class CreditLedger(db.Model):
    """Model for tracking all credit transactions (grants, consumption, refunds, adjustments)"""
    __tablename__ = 'credit_ledger'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    month = db.Column(db.String(7), nullable=False, index=True)  # Format: YYYY-MM
    delta_credits = db.Column(db.Integer, nullable=False)  # Positive for grants/refunds, negative for consumption
    reason = db.Column(db.String(50), nullable=False, index=True)  # 'monthly_grant', 'job_reserve', 'job_final', 'job_refund', 'admin_adjustment'
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=True, index=True)
    pricing_version = db.Column(db.String(20), nullable=True)  # Track pricing version for auditing
    description = db.Column(db.String(255), nullable=True)  # Human-readable description
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow, nullable=False)
    
    # Composite index for efficient balance queries
    __table_args__ = (
        Index('idx_user_month', 'user_id', 'month'),
    )
    
    def __repr__(self):
        return f'<CreditLedger user_id={self.user_id} month={self.month} delta={self.delta_credits} reason={self.reason}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'month': self.month,
            'delta_credits': self.delta_credits,
            'reason': self.reason,
            'job_id': self.job_id,
            'pricing_version': self.pricing_version,
            'description': self.description,
            'timestamp': self.timestamp.isoformat() + 'Z'
        }


class Job(db.Model):
    """Model for tracking processing jobs with credit usage"""
    __tablename__ = 'jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    history_id = db.Column(db.Integer, db.ForeignKey('history.id'), nullable=True, index=True)  # Link to history entry
    status = db.Column(db.String(20), nullable=False, index=True, default='pending')  # 'pending', 'processing', 'completed', 'failed', 'cancelled'
    
    # File/processing info
    original_filename = db.Column(db.String(128), nullable=False)
    model = db.Column(db.String(50), nullable=False)  # 'gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.5-flash-lite'
    
    # Token and credit tracking
    estimated_tokens = db.Column(db.Integer, nullable=True)  # Estimated before processing
    actual_tokens = db.Column(db.Integer, nullable=True)  # Actual tokens used
    estimated_credits = db.Column(db.Integer, nullable=False)  # Credits reserved
    actual_credits = db.Column(db.Integer, nullable=True)  # Credits actually consumed
    
    # Pricing info
    pricing_version = db.Column(db.String(20), nullable=False)  # Version of pricing used
    pricing_rate = db.Column(db.Float, nullable=False)  # Credits per 1K tokens at time of job
    
    # Processing settings snapshot
    processing_settings = db.Column(db.JSON, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, index=True, default=datetime.utcnow, nullable=False)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Error info
    error_message = db.Column(db.String(512), nullable=True)
    error_code = db.Column(db.String(50), nullable=True)
    
    # Async processing fields
    celery_task_id = db.Column(db.String(155), nullable=True, index=True)  # Celery task ID for tracking
    progress_percent = db.Column(db.Integer, default=0)  # 0-100
    current_step = db.Column(db.String(100), nullable=True)  # "Chunking PDF", "Processing chunk 5/10"
    total_chunks = db.Column(db.Integer, nullable=True)
    processed_chunks = db.Column(db.Integer, default=0)
    
    # Resource management
    chunk_results = db.Column(db.JSON, nullable=True)  # [{chunk_id: 1, sentences: [...], status: 'done'}]
    failed_chunks = db.Column(db.JSON, nullable=True)  # [2, 7] - chunk IDs that failed
    retry_count = db.Column(db.Integer, default=0)
    max_retries = db.Column(db.Integer, default=3)
    
    # Cancellation support
    is_cancelled = db.Column(db.Boolean, default=False)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    cancelled_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Performance metrics
    processing_time_seconds = db.Column(db.Integer, nullable=True)
    gemini_api_calls = db.Column(db.Integer, default=0)
    gemini_tokens_used = db.Column(db.Integer, default=0)
    
    # Relationships
    ledger_entries = db.relationship('CreditLedger', backref='job', lazy='dynamic')
    chunks = db.relationship('JobChunk', backref='job', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Job id={self.id} user_id={self.user_id} status={self.status} file={self.original_filename}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'history_id': self.history_id,
            'status': self.status,
            'original_filename': self.original_filename,
            'model': self.model,
            'estimated_tokens': self.estimated_tokens,
            'actual_tokens': self.actual_tokens,
            'estimated_credits': self.estimated_credits,
            'actual_credits': self.actual_credits,
            'pricing_version': self.pricing_version,
            'pricing_rate': self.pricing_rate,
            'processing_settings': self.processing_settings,
            'created_at': self.created_at.isoformat() + 'Z',
            'started_at': self.started_at.isoformat() + 'Z' if self.started_at else None,
            'completed_at': self.completed_at.isoformat() + 'Z' if self.completed_at else None,
            'error_message': self.error_message,
            'error_code': self.error_code,
            'celery_task_id': self.celery_task_id,
            'progress_percent': self.progress_percent,
            'current_step': self.current_step,
            'total_chunks': self.total_chunks,
            'processed_chunks': self.processed_chunks,
            'chunk_results': self.chunk_results,
            'failed_chunks': self.failed_chunks,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'is_cancelled': self.is_cancelled,
            'cancelled_at': self.cancelled_at.isoformat() + 'Z' if self.cancelled_at else None,
            'cancelled_by': self.cancelled_by,
            'processing_time_seconds': self.processing_time_seconds,
            'gemini_api_calls': self.gemini_api_calls,
            'gemini_tokens_used': self.gemini_tokens_used
        }


class JobChunk(db.Model):
    """Model for tracking individual PDF chunk processing"""
    __tablename__ = 'job_chunks'
    
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False, index=True)
    chunk_id = db.Column(db.Integer, nullable=False)  # 0-indexed chunk number
    
    # Chunk metadata
    start_page = db.Column(db.Integer, nullable=False)
    end_page = db.Column(db.Integer, nullable=False)
    page_count = db.Column(db.Integer, nullable=False)
    has_overlap = db.Column(db.Boolean, default=False)
    
    # Chunk payload (base64 PDF chunk data)
    file_b64 = db.Column(db.Text)
    storage_url = db.Column(db.String(512))  # Future: S3/GCS URL
    file_size_bytes = db.Column(db.Integer)
    
    # Processing state
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)
    # Status values: 'pending', 'processing', 'success', 'failed', 'retry_scheduled'
    celery_task_id = db.Column(db.String(155))  # Current/last task processing this chunk
    
    # Retry tracking
    attempts = db.Column(db.Integer, default=0)
    max_retries = db.Column(db.Integer, default=3)
    last_error = db.Column(db.Text)
    last_error_code = db.Column(db.String(50))
    
    # Results (when successful)
    result_json = db.Column(db.JSON)  # {sentences: [...], tokens: 123, status: 'success'}
    processed_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('job_id', 'chunk_id', name='unique_job_chunk'),
        db.Index('idx_job_chunks_job_status', 'job_id', 'status'),
    )
    
    def __repr__(self):
        return f'<JobChunk job_id={self.job_id} chunk_id={self.chunk_id} status={self.status}>'
    
    def to_dict(self):
        """Convert JobChunk to dictionary for API responses"""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'chunk_id': self.chunk_id,
            'start_page': self.start_page,
            'end_page': self.end_page,
            'page_count': self.page_count,
            'has_overlap': self.has_overlap,
            'status': self.status,
            'attempts': self.attempts,
            'max_retries': self.max_retries,
            'last_error': self.last_error,
            'last_error_code': self.last_error_code,
            'processed_at': self.processed_at.isoformat() + 'Z' if self.processed_at else None,
            'created_at': self.created_at.isoformat() + 'Z',
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
        }
    
    def can_retry(self) -> bool:
        """Check if chunk can be retried based on status and attempts"""
        return self.status in ['failed', 'retry_scheduled'] and self.attempts < self.max_retries
    
    def get_chunk_metadata(self):
        """Build chunk metadata dict for process_chunk task"""
        return {
            'chunk_id': self.chunk_id,
            'job_id': self.job_id,
            'file_b64': self.file_b64,
            'storage_url': self.storage_url,
            'start_page': self.start_page,
            'end_page': self.end_page,
            'page_count': self.page_count,
            'has_overlap': self.has_overlap,
        }
