import os
import sys
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app


def test_github_callback_success():
    """Verify that /github/callback saves the installation ID and redirects to the dashboard."""
    client = TestClient(app)
    
    with patch("api.main.save_installation_id") as mock_save:
        with patch.dict(os.environ, {"DASHBOARD_URL": "http://localhost:8501"}):
            response = client.get("/github/callback?installation_id=55555&setup_action=install", follow_redirects=False)
            
            # FastAPI RedirectResponse returns 307 Temporary Redirect by default
            assert response.status_code == 307
            assert response.headers["location"] == "http://localhost:8501"
            mock_save.assert_called_once_with(55555)


def test_github_callback_missing_id():
    """Verify that /github/callback returns 422 or error when installation_id is missing."""
    client = TestClient(app)
    
    response = client.get("/github/callback")
    # FastAPI returns 422 Unprocessable Entity for missing required query parameters
    assert response.status_code == 422


def test_scan_endpoint_github_app_success(tmp_path, monkeypatch):
    """Verify /scan endpoint permits access and scans successfully when GitHub App auth is valid."""
    client = TestClient(app)
    
    repo_path = tmp_path / "repo"
    (repo_path / "src").mkdir(parents=True, exist_ok=True)
    (repo_path / "src" / "sample.py").write_text("value = 42\n", encoding="utf-8")
    
    monkeypatch.setenv("USE_GITHUB_APP", "true")
    
    with patch("api.main.load_installation_id", return_value=55555):
        with patch("src.github_auth.check_repository_access", return_value=True):
            monkeypatch.setattr("src.scanner.clone_repository", lambda repository_url, destination=None: str(repo_path))
            
            response = client.post(
                "/scan",
                json={"repository_url": "https://github.com/example/demo"}
            )
            
            assert response.status_code == 200
            payload = response.json()
            assert payload["status"] == "completed"
            assert payload["repository"] == "https://github.com/example/demo"


def test_scan_endpoint_github_app_access_denied(monkeypatch):
    """Verify /scan endpoint returns 403 Forbidden when GitHub App lacks repo access."""
    client = TestClient(app)
    
    monkeypatch.setenv("USE_GITHUB_APP", "true")
    
    with patch("api.main.load_installation_id", return_value=55555):
        with patch("src.github_auth.check_repository_access", return_value=False):
            response = client.post(
                "/scan",
                json={"repository_url": "https://github.com/example/demo"}
            )
            
            assert response.status_code == 403
            assert "Access Denied" in response.json()["detail"]
