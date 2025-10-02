from datetime import datetime
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
    min_sentence_length = db.Column(db.Integer, default=3)
    
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
