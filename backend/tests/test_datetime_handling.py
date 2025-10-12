"""Tests for timezone-aware datetime handling in OAuth token expiry"""
import pytest
from datetime import datetime, timedelta, timezone
from app import create_app, db
from app.models import User
from app.services.auth_service import AuthService
from config import Config


class TestConfig(Config):
    """Test configuration that works with SQLite"""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GOOGLE_CLIENT_ID = "test_client_id"
    GOOGLE_CLIENT_SECRET = "test_client_secret"
    # Override engine options for SQLite compatibility
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}


@pytest.fixture(scope="function")
def app():
    """Create application for testing"""
    app = create_app(config_class=TestConfig)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def sample_user(app):
    """Create a sample user for testing"""
    user = User(
        email="test@example.com",
        name="Test User",
        google_id="test123",
        is_active=True,
        google_access_token="test_access_token",
        google_refresh_token="test_refresh_token",
    )
    db.session.add(user)
    db.session.commit()
    return user


class TestDatetimeHandling:
    """Tests for timezone-aware datetime handling"""

    def test_naive_datetime_expiry_is_normalized(self, app, sample_user):
        """Test that naive datetime expiry values are normalized to timezone-aware UTC"""
        # Set a naive datetime expiry (no timezone info)
        naive_expiry = datetime.utcnow() + timedelta(hours=1)
        assert naive_expiry.tzinfo is None, "Test setup: expiry should be naive"

        sample_user.google_token_expiry = naive_expiry
        db.session.commit()

        # AuthService should handle this without raising TypeError
        auth_service = AuthService()

        # This should NOT raise "can't compare offset-naive and offset-aware datetimes"
        try:
            # get_user_credentials internally compares expiry with datetime.now(timezone.utc)
            # If the stored expiry is naive, it should be normalized before comparison
            credentials = auth_service.get_user_credentials(sample_user)
            # If we get here without exception, the normalization worked
            assert True
        except TypeError as e:
            if "can't compare offset-naive and offset-aware datetimes" in str(e):
                pytest.fail(f"Datetime comparison failed: {e}")
            else:
                raise

    def test_aware_datetime_expiry_works(self, app, sample_user):
        """Test that timezone-aware datetime expiry values work correctly"""
        # Set an aware datetime expiry (with timezone info)
        aware_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        assert aware_expiry.tzinfo is not None, "Test setup: expiry should be timezone-aware"

        sample_user.google_token_expiry = aware_expiry
        db.session.commit()

        # AuthService should handle this normally
        auth_service = AuthService()

        # This should work without any issues
        try:
            credentials = auth_service.get_user_credentials(sample_user)
            assert credentials is not None
        except TypeError as e:
            pytest.fail(f"Datetime comparison failed with aware datetime: {e}")

    def test_expired_naive_token_comparison(self, app, sample_user):
        """Test comparison when token is expired and stored as naive datetime"""
        # Set an expired naive datetime (1 hour ago)
        expired_naive = datetime.utcnow() - timedelta(hours=1)
        assert expired_naive.tzinfo is None, "Test setup: expiry should be naive"

        sample_user.google_token_expiry = expired_naive
        db.session.commit()

        # AuthService should detect expiry without raising TypeError
        auth_service = AuthService()

        try:
            # This should detect the token is expired and attempt refresh
            # Since we don't have valid refresh credentials, it will fail at refresh
            # But it should NOT fail at the datetime comparison stage
            credentials = auth_service.get_user_credentials(sample_user)
            # We may get here or may raise ValueError from refresh attempt
        except ValueError as e:
            # Expected: refresh will fail with our test tokens
            # But the error should NOT be about datetime comparison
            assert "can't compare" not in str(e).lower()
        except TypeError as e:
            if "can't compare offset-naive and offset-aware datetimes" in str(e):
                pytest.fail(f"Datetime comparison failed with naive expired token: {e}")
            else:
                raise

    def test_get_or_create_user_normalizes_expiry(self, app):
        """Test that get_or_create_user normalizes token expiry for safe comparisons"""
        auth_service = AuthService()

        google_user_info = {
            "google_id": "new_user_123",
            "email": "newuser@example.com",
            "name": "New User",
            "picture": "http://example.com/pic.jpg",
        }

        # Provide a naive datetime expiry
        naive_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        # Convert to naive for testing
        naive_expiry = naive_expiry.replace(tzinfo=None)
        oauth_tokens = {
            "access_token": "test_token",
            "refresh_token": "test_refresh",
            "expiry": naive_expiry,
        }

        # Create user with naive expiry
        user = auth_service.get_or_create_user(google_user_info, oauth_tokens)

        # The stored expiry may be naive (database limitation), but comparisons should work
        # Test that we can safely compare using get_user_credentials which normalizes before comparison
        if user.google_token_expiry:
            try:
                # get_user_credentials normalizes the stored expiry before comparing
                # This should NOT raise TypeError
                credentials = auth_service.get_user_credentials(user)
                assert credentials is not None, "Should be able to get credentials"
                assert True  # If we get here, normalization worked
            except TypeError as e:
                if "can't compare offset-naive and offset-aware datetimes" in str(e):
                    pytest.fail(f"Stored expiry not properly normalized during comparison: {e}")
                else:
                    raise

    def test_iso_string_expiry_is_parsed_and_normalized(self, app):
        """Test that ISO string expiry values are parsed and can be safely compared"""
        auth_service = AuthService()

        google_user_info = {
            "google_id": "string_expiry_user",
            "email": "stringuser@example.com",
            "name": "String User",
            "picture": "http://example.com/pic.jpg",
        }

        # Provide expiry as ISO string (common in OAuth responses)
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        iso_expiry = future_time.isoformat()

        oauth_tokens = {
            "access_token": "test_token",
            "refresh_token": "test_refresh",
            "expiry": iso_expiry,
        }

        # Create user with string expiry
        user = auth_service.get_or_create_user(google_user_info, oauth_tokens)

        # The expiry should be stored as datetime and safe to compare via get_user_credentials
        if user.google_token_expiry:
            try:
                # get_user_credentials normalizes the stored expiry before comparing
                credentials = auth_service.get_user_credentials(user)
                assert credentials is not None, "Should be able to get credentials"
                assert True  # If we get here, normalization worked
            except TypeError as e:
                if "can't compare offset-naive and offset-aware datetimes" in str(e):
                    pytest.fail(f"ISO string expiry not properly handled during comparison: {e}")
                else:
                    raise
