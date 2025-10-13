"""Tests for the /estimate-pdf endpoint"""
import pytest
import os
import sys
from io import BytesIO
from unittest.mock import patch, MagicMock
from werkzeug.datastructures import FileStorage

# Add the backend directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.models import User
from config import Config


class TestConfig(Config):
    """Test configuration"""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    RATELIMIT_ENABLED = False  # Disable rate limiting for tests
    JWT_SECRET_KEY = "test-secret-key"


# Override SQLALCHEMY_ENGINE_OPTIONS after class definition for SQLite compatibility
TestConfig.SQLALCHEMY_ENGINE_OPTIONS = {}


@pytest.fixture
def app():
    """Create test Flask app"""
    test_app = create_app(TestConfig)

    with test_app.app_context():
        db.create_all()

        # Create test user
        test_user = User(
            email="test@example.com", name="Test User", google_id="test-google-id", is_active=True
        )
        db.session.add(test_user)
        db.session.commit()

        yield test_app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def auth_headers(app):
    """Create JWT auth headers for test user"""
    from flask_jwt_extended import create_access_token

    with app.app_context():
        user = User.query.filter_by(email="test@example.com").first()
        access_token = create_access_token(identity=str(user.id))
        return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def mock_pdf_file():
    """Create a mock PDF file"""
    pdf_content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R>>endobj
4 0 obj<</Length 44>>stream
BT
/F1 12 Tf
72 720 Td
(Hello World) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000052 00000 n 
0000000101 00000 n 
0000000181 00000 n 
trailer<</Size 5/Root 1 0 R>>
startxref
273
%%EOF"""
    return FileStorage(
        stream=BytesIO(pdf_content), filename="test.pdf", content_type="application/pdf"
    )


def test_estimate_pdf_success(client, auth_headers, mock_pdf_file):
    """Test successful PDF estimation"""
    data = {"pdf_file": mock_pdf_file, "model_preference": "balanced"}

    response = client.post(
        "/api/v1/estimate-pdf", data=data, headers=auth_headers, content_type="multipart/form-data"
    )

    assert response.status_code == 200
    json_data = response.get_json()

    # Verify response structure
    assert "page_count" in json_data
    assert "file_size" in json_data
    assert "image_count" in json_data
    assert "estimated_tokens" in json_data
    assert "estimated_credits" in json_data
    assert "model" in json_data
    assert "model_preference" in json_data
    assert "pricing_rate" in json_data
    assert "capped" in json_data

    # Verify values
    assert json_data["page_count"] == 1
    assert json_data["file_size"] > 0
    assert json_data["estimated_tokens"] > 0
    assert json_data["estimated_credits"] > 0
    assert json_data["model_preference"] == "balanced"
    assert json_data["capped"] is False


def test_estimate_pdf_different_models(client, auth_headers):
    """Test estimation with different model preferences"""
    for model_pref in ["balanced", "quality", "speed"]:
        # Create fresh PDF file for each iteration
        pdf_content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R>>endobj
4 0 obj<</Length 44>>stream
BT
/F1 12 Tf
72 720 Td
(Hello World) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000052 00000 n 
0000000101 00000 n 
0000000181 00000 n 
trailer<</Size 5/Root 1 0 R>>
startxref
273
%%EOF"""
        mock_pdf = FileStorage(
            stream=BytesIO(pdf_content), filename="test.pdf", content_type="application/pdf"
        )

        data = {"pdf_file": mock_pdf, "model_preference": model_pref}

        response = client.post(
            "/api/v1/estimate-pdf",
            data=data,
            headers=auth_headers,
            content_type="multipart/form-data",
        )

        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["model_preference"] == model_pref


def test_estimate_pdf_no_auth(client, mock_pdf_file):
    """Test estimation without authentication"""
    data = {"pdf_file": mock_pdf_file}

    response = client.post("/api/v1/estimate-pdf", data=data, content_type="multipart/form-data")

    assert response.status_code == 401


def test_estimate_pdf_no_file(client, auth_headers):
    """Test estimation without file"""
    response = client.post(
        "/api/v1/estimate-pdf", data={}, headers=auth_headers, content_type="multipart/form-data"
    )

    assert response.status_code == 400
    json_data = response.get_json()
    assert "error" in json_data
    assert "No PDF file provided" in json_data["error"]


def test_estimate_pdf_invalid_file(client, auth_headers):
    """Test estimation with invalid PDF"""
    invalid_file = FileStorage(
        stream=BytesIO(b"Not a PDF"), filename="test.pdf", content_type="application/pdf"
    )

    data = {"pdf_file": invalid_file}

    response = client.post(
        "/api/v1/estimate-pdf", data=data, headers=auth_headers, content_type="multipart/form-data"
    )

    assert response.status_code == 422
    json_data = response.get_json()
    assert "error" in json_data


def test_estimate_pdf_invalid_model_preference(client, auth_headers, mock_pdf_file):
    """Test estimation with invalid model preference"""
    data = {"pdf_file": mock_pdf_file, "model_preference": "invalid_model"}

    response = client.post(
        "/api/v1/estimate-pdf", data=data, headers=auth_headers, content_type="multipart/form-data"
    )

    assert response.status_code == 400
    json_data = response.get_json()
    assert "error" in json_data


def test_estimate_pdf_capped_pages(client, auth_headers):
    """Test estimation with page count exceeding cap"""
    # Create a mock PDF service that returns high page count
    from app.constants import MAX_PAGES_FOR_ESTIMATE

    with patch("app.routes.PDFService") as mock_service:
        mock_instance = MagicMock()
        mock_instance.get_page_count.return_value = {
            "page_count": MAX_PAGES_FOR_ESTIMATE + 100,
            "file_size": 50000000,
            "image_count": 10,
        }
        mock_service.return_value = mock_instance

        mock_pdf_file = FileStorage(
            stream=BytesIO(b"%PDF-1.4\ntest"), filename="large.pdf", content_type="application/pdf"
        )

        data = {"pdf_file": mock_pdf_file}

        response = client.post(
            "/api/v1/estimate-pdf",
            data=data,
            headers=auth_headers,
            content_type="multipart/form-data",
        )

        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["capped"] is True
        assert json_data["warning"] is not None
        assert "exceeds maximum" in json_data["warning"]


def test_estimate_pdf_no_history_created(client, auth_headers, mock_pdf_file, app):
    """Test that estimation does not create history entries"""
    from app.models import History

    with app.app_context():
        # Count history entries before
        history_count_before = History.query.count()

        data = {"pdf_file": mock_pdf_file}

        response = client.post(
            "/api/v1/estimate-pdf",
            data=data,
            headers=auth_headers,
            content_type="multipart/form-data",
        )

        assert response.status_code == 200

        # Verify no new history entry was created
        history_count_after = History.query.count()
        assert history_count_after == history_count_before


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
