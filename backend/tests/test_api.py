# backend/tests/test_api.py

import pytest
import json
import io
from app import create_app


@pytest.fixture
def client():
    """Create test Flask client."""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_upload_no_files(client):
    """Test that upload without files returns 400."""
    response = client.post("/api/upload")
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data


def test_chat_no_session(client):
    """Test that chat without session_id returns 400."""
    response = client.post(
        "/api/chat",
        json={"question": "What is this about?"},
        content_type="application/json"
    )
    assert response.status_code == 400


def test_chat_empty_question(client):
    """Test that empty question returns 400."""
    response = client.post(
        "/api/chat",
        json={"question": "", "session_id": "test-session"},
        content_type="application/json"
    )
    assert response.status_code == 400


def test_documents_no_session(client):
    """Test that documents endpoint without session returns 400."""
    response = client.get("/api/documents")
    assert response.status_code == 400


def test_health_check(client):
    """Documents list returns 200 with valid session."""
    response = client.get("/api/documents?session_id=test-123")
    assert response.status_code == 200