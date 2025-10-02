import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from config import Config
from .utils.error_handlers import register_error_handlers
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[]
)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Configure CORS with whitelist and credentials support
    CORS(app, 
         origins=app.config['CORS_ORIGINS'],
         supports_credentials=app.config['CORS_SUPPORTS_CREDENTIALS'])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    
    if app.config['RATELIMIT_ENABLED']:
        limiter.init_app(app)
    
    # Configure logging
    configure_logging(app)

    with app.app_context():
        # Import models first so SQLAlchemy knows about them
        from . import models  # Import models to register them with SQLAlchemy

        # NOTE: db.create_all() is disabled because we use Flask-Migrate for database management
        # Run migrations instead: flask db upgrade
        
        # Import routes after models are loaded
        from . import routes
        from . import auth_routes

        # Register blueprints
        app.register_blueprint(routes.main_bp, url_prefix='/api/v1')
        app.register_blueprint(auth_routes.auth_bp, url_prefix='/api/v1/auth')

        # Register error handlers
        register_error_handlers(app)

    return app

def configure_logging(app):
    """Configure application logging"""
    if not app.debug and not app.testing:
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(app.config['LOG_FILE'])
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # File handler
        file_handler = RotatingFileHandler(
            app.config['LOG_FILE'],
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
