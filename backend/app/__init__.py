import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from config import Config
from .utils.error_handlers import register_error_handlers
from flask_sqlalchemy import SQLAlchemy
from .celery_app import make_celery
from .extensions import db
migrate = Migrate()
jwt = JWTManager()

def _get_remote_address_for_limiter():
    """Custom key function for rate limiter that exempts OPTIONS requests"""
    from flask import request
    if request.method == 'OPTIONS':
        return '__OPTIONS_EXEMPT__'  # Use special key for OPTIONS to bypass rate limiting
    return get_remote_address()

limiter = Limiter(
    key_func=_get_remote_address_for_limiter,
    default_limits=[]
)
socketio = SocketIO()
celery = None  # Will be initialized in create_app

def create_app(config_class=Config, skip_logging=False):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # --- CORS Configuration ---
    # Centralize CORS origin parsing to ensure consistency for Flask-CORS and Socket.IO
    origins_config = app.config.get('CORS_ORIGINS', '')
    if isinstance(origins_config, str):
        # Split comma-separated string into a list of origins, filtering out empty strings
        origins = [origin.strip() for origin in origins_config.split(',') if origin.strip()]
    elif isinstance(origins_config, list):
        origins = origins_config
    else:
        origins = []

    # Provide a sensible default for development if no origins are configured
    if not origins and app.config.get('FLASK_ENV') == 'development':
        origins = ['http://localhost:3000', 'http://127.0.0.1:3000']
    
    if not origins and app.config.get('FLASK_ENV') != 'development':
        app.logger.warning(
            "CORS_ORIGINS is not set or empty in a non-development environment. "
            "Frontend applications will not be able to connect."
        )
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    
    if app.config['RATELIMIT_ENABLED']:
        limiter.init_app(app)
    
    # Use the parsed origins list for both Socket.IO and Flask-CORS
    socketio.init_app(
        app,
        cors_allowed_origins=origins,
        message_queue=app.config.get('CELERY_BROKER_URL'),
        async_mode='eventlet'
    )
    CORS(
        app,
        origins=origins,
        supports_credentials=True,
        allow_headers=['Content-Type', 'Authorization'],
        methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        expose_headers=['Content-Type', 'Authorization']
    )
    
    # Initialize Celery
    global celery
    celery = make_celery(app)
    
    # Configure logging
    if not skip_logging:
        configure_logging(app)

    with app.app_context():
        # Import models first so SQLAlchemy knows about them
        from . import models  # Import models to register them with SQLAlchemy

        # NOTE: db.create_all() is disabled because we use Flask-Migrate for database management
        # Run migrations instead: flask db upgrade
        
        # Import routes after models are loaded
        from . import routes
        from . import auth_routes
        from . import credit_routes
        from . import coverage_routes
        from . import wordlist_routes

        # Register blueprints
        app.register_blueprint(routes.main_bp, url_prefix='/api/v1')
        app.register_blueprint(auth_routes.auth_bp, url_prefix='/api/v1/auth')
        app.register_blueprint(credit_routes.credit_bp, url_prefix='/api/v1/credits')
        app.register_blueprint(coverage_routes.coverage_bp)
        app.register_blueprint(wordlist_routes.wordlist_bp)

        # Register error handlers
        register_error_handlers(app)

        # Set up enhanced CORS handling - REMOVED to avoid duplicate headers
        # setup_cors_handling(app)

        # Handle OPTIONS requests globally (for CORS preflight)
        @app.before_request
        def handle_preflight():
            from flask import request, make_response
            if request.method == 'OPTIONS':
                # Return 200 OK for all OPTIONS requests
                response = make_response('', 200)
                return response

        # Register SocketIO event handlers
        from . import socket_events  # Import to register handlers

        # Initialize global wordlist (ensure default exists)
        # Run this in a background daemon thread to avoid blocking app startup
        # and healthchecks. The initializer is idempotent and logs failures.
        if not app.config.get('TESTING', False):
            try:
                import threading

                t = threading.Thread(target=initialize_global_wordlist, args=(app,), daemon=True)
                t.start()
            except Exception as e:
                app.logger.warning(f"Failed to start background global wordlist initializer: {e}")

    return app


def initialize_global_wordlist(app):
    """
    Ensure global default wordlist exists on app startup.
    This is idempotent and safe to run on every startup.
    
    NOTE: This runs in a background thread, so it needs an app context.
    """
    # In a multi-worker setup (like Gunicorn), this function will be called by each worker.
    # We need a lock to prevent a race condition where multiple workers try to create the
    # global wordlist simultaneously.
    
    # The lock file should be in a location accessible by all workers.
    # /tmp is a good candidate in containerized environments.
    lock_file_path = '/tmp/global_wordlist.lock'
    
    try:
        # Attempt to acquire the lock. This is an atomic operation.
        # os.O_CREAT | os.O_EXCL will fail if the file already exists.
        lock_fd = os.open(lock_file_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        # Another worker has acquired the lock, so this worker can exit.
        app.logger.info("Global wordlist initialization is already in progress by another worker.")
        return

    try:
        with app.app_context():
            try:
                from app.services.global_wordlist_manager import GlobalWordlistManager
                
                # This will create the wordlist if it doesn't exist
                wordlist = GlobalWordlistManager.ensure_global_default_exists()
                
                if wordlist:
                    app.logger.info(
                        f"Global default wordlist ready: {wordlist.name} "
                        f"(ID: {wordlist.id}, {wordlist.normalized_count} words)"
                    )
            except Exception as e:
                # Log error but don't crash the app
                app.logger.warning(f"Failed to initialize global wordlist: {e}", exc_info=True)
                app.logger.warning("App will continue but users may not have a default wordlist available")
    finally:
        # Release the lock by closing and deleting the file
        os.close(lock_fd)
        os.remove(lock_file_path)
        app.logger.info("Global wordlist initialization finished and lock released.")

def configure_logging(app):
    """Configure application logging"""
    if not app.debug and not app.testing:
        # The Dockerfile creates /app/logs and chowns it to appuser.
        # This path is guaranteed to be writable.
        log_dir = '/app/logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, 'app.log')

        # File handler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
        ))
        file_handler.setLevel(getattr(logging, app.config['LOG_LEVEL']))
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))
        app.logger.info('French Novel Tool startup')
