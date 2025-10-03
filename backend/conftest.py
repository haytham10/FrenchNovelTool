"""
Pytest configuration and fixtures for backend tests
"""
import os
import sys
import tempfile
import pytest
from datetime import datetime

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, UserSettings
from config import Config


class TestConfig(Config):
    """Test configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test-secret-key'
    JWT_SECRET_KEY = 'test-jwt-secret'
    GEMINI_API_KEY = 'test-gemini-key'
    RATELIMIT_ENABLED = False
    CHUNKING_THRESHOLD_PAGES = 50
    CHUNK_SIZE_PAGES = 50
    WTF_CSRF_ENABLED = False


@pytest.fixture(scope='function')
def app():
    """Create and configure a test Flask application instance"""
    app = create_app(TestConfig)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Create a test client for the app"""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """Create a test CLI runner for the app"""
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def test_user(app):
    """Create a test user"""
    with app.app_context():
        user = User(
            email='test@example.com',
            name='Test User',
            google_id='test123',
            is_active=True,
            created_at=datetime.utcnow(),
            last_login=datetime.utcnow()
        )
        db.session.add(user)
        db.session.commit()
        
        # Create user settings
        settings = UserSettings(
            user_id=user.id,
            sentence_length_limit=8,
            gemini_model='balanced',
            ignore_dialogue=False,
            preserve_formatting=True,
            fix_hyphenation=True,
            min_sentence_length=2
        )
        db.session.add(settings)
        db.session.commit()
        
        return user.id


@pytest.fixture(scope='function')
def auth_headers(app, test_user):
    """Create authentication headers for API requests"""
    from flask_jwt_extended import create_access_token
    
    with app.app_context():
        access_token = create_access_token(identity=str(test_user))
        return {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }


@pytest.fixture(scope='function')
def temp_pdf():
    """Create a temporary PDF file for testing"""
    from PyPDF2 import PdfWriter
    
    pdf_writer = PdfWriter()
    # Create a PDF with 10 pages
    for i in range(10):
        pdf_writer.add_blank_page(width=612, height=792)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        pdf_writer.write(temp_file)
        temp_path = temp_file.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture(scope='function')
def large_pdf():
    """Create a large PDF file (100 pages) for testing"""
    from PyPDF2 import PdfWriter
    
    pdf_writer = PdfWriter()
    # Create a PDF with 100 pages
    for i in range(100):
        pdf_writer.add_blank_page(width=612, height=792)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        pdf_writer.write(temp_file)
        temp_path = temp_file.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)
