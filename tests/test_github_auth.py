"""
test_github_auth.py — Unit tests for the GitHub App authentication layer.
"""

import os
import sys
import time
import pytest
import requests
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, ANY

# Ensure Python can find the src directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import jwt

# Generate a real RSA private key for testing JWT encoding/decoding
_private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)
TEST_PRIVATE_KEY = _private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
).decode('utf-8')

# Expose the public key for verifying JWTs in tests
TEST_PUBLIC_KEY = _private_key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode('utf-8')


from src import github_auth
from src.github_auth import (
    create_app_jwt,
    get_installation_token,
    get_installation_info,
    authenticated_github_client,
    save_installation_id,
    load_installation_id,
    get_app_info,
    list_installation_repositories,
    check_repository_access,
    InvalidAppConfigError,
    InvalidPrivateKeyError,
    JWTGenerationError,
    InstallationTokenRequestError,
    ExpiredJWTError,
    GitHubAPIError
)


@pytest.fixture(autouse=True)
def setup_auth_env(monkeypatch):
    """
    Automatically mock module-level configuration variables in src.github_auth
    for every test, and clear the in-memory token cache.
    """
    monkeypatch.setattr(github_auth, "GITHUB_APP_ID", "123456")
    monkeypatch.setattr(github_auth, "GITHUB_PRIVATE_KEY", TEST_PRIVATE_KEY)
    monkeypatch.setattr(github_auth, "GITHUB_WEBHOOK_SECRET", "test_webhook_sec")
    
    # Delete environment variables to prevent test contamination from local .env
    monkeypatch.delenv("GITHUB_INSTALLATION_ID", raising=False)
    monkeypatch.delenv("USE_GITHUB_APP", raising=False)
    
    with github_auth._cache_lock:
        github_auth._token_cache.clear()


def test_create_app_jwt_success():
    """Verify that create_app_jwt generates a valid RS256 JWT signed with the private key."""
    token = create_app_jwt()
    assert isinstance(token, str)
    
    # Decode and verify token using the public key
    decoded = jwt.decode(token, TEST_PUBLIC_KEY, algorithms=["RS256"])
    assert decoded["iss"] == "123456"
    # Verify expiration (exp should be greater than now)
    assert decoded["exp"] > time.time()
    # Verify iat
    assert decoded["iat"] < time.time()


def test_create_app_jwt_missing_app_id(monkeypatch):
    """Test JWT generation failure when GITHUB_APP_ID is missing."""
    monkeypatch.setattr(github_auth, "GITHUB_APP_ID", "")
    with pytest.raises(InvalidAppConfigError) as exc_info:
        create_app_jwt()
    assert "GITHUB_APP_ID is not configured" in str(exc_info.value)


def test_create_app_jwt_non_int_app_id(monkeypatch):
    """Test JWT generation failure when GITHUB_APP_ID is not a valid integer."""
    monkeypatch.setattr(github_auth, "GITHUB_APP_ID", "not-an-integer")
    with pytest.raises(InvalidAppConfigError) as exc_info:
        create_app_jwt()
    assert "must be a numeric integer" in str(exc_info.value)


def test_load_private_key_file_success(tmp_path, monkeypatch):
    """Test loading a valid private key from a file path."""
    key_file = tmp_path / "test_key.pem"
    key_file.write_text(TEST_PRIVATE_KEY)
    
    monkeypatch.setattr(github_auth, "GITHUB_PRIVATE_KEY", str(key_file))
    token = create_app_jwt()
    assert isinstance(token, str)


def test_load_private_key_file_not_found(monkeypatch):
    """Test private key load failure when path does not exist and is not a valid PEM string."""
    monkeypatch.setattr(github_auth, "GITHUB_PRIVATE_KEY", "/non/existent/path/to/key.pem")
    with pytest.raises(InvalidPrivateKeyError) as exc_info:
        create_app_jwt()
    assert "neither a valid file path nor a valid PEM" in str(exc_info.value)


def test_load_private_key_invalid_pem(monkeypatch):
    """Test private key load failure when the PEM content is malformed."""
    monkeypatch.setattr(github_auth, "GITHUB_PRIVATE_KEY", "malformed key content")
    with pytest.raises(InvalidPrivateKeyError) as exc_info:
        create_app_jwt()
    assert "neither a valid file path nor a valid PEM" in str(exc_info.value)


def test_get_installation_token_success():
    """Verify get_installation_token successfully fetches and returns the access token."""
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "token": "ghs_testinstallationtoken123",
        "expires_at": "2026-07-16T16:32:00Z"
    }
    
    with patch("requests.post", return_value=mock_response) as mock_post:
        token = get_installation_token(98765)
        
        assert token == "ghs_testinstallationtoken123"
        mock_post.assert_called_once()
        # Verify the headers contain Bearer token authorization
        args, kwargs = mock_post.call_args
        assert "Authorization" in kwargs["headers"]
        assert kwargs["headers"]["Authorization"].startswith("Bearer ")


def test_get_installation_token_caching():
    """Verify that get_installation_token caches the token and does not request a new one."""
    mock_response = MagicMock()
    mock_response.status_code = 201
    # Set expires_at to 30 minutes in the future so caching is valid
    future_time = (datetime.now(timezone.utc) + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    mock_response.json.return_value = {
        "token": "ghs_cachedtoken",
        "expires_at": future_time
    }
    
    with patch("requests.post", return_value=mock_response) as mock_post:
        # First call
        token1 = get_installation_token(1111)
        # Second call should read from cache
        token2 = get_installation_token(1111)
        
        assert token1 == "ghs_cachedtoken"
        assert token2 == "ghs_cachedtoken"
        mock_post.assert_called_once()


def test_get_installation_token_refresh_on_expiration():
    """Verify that get_installation_token fetches a new token if cached token is expired/expiring soon."""
    # Seed cache with an already expired token
    past_time = (datetime.now(timezone.utc) - timedelta(minutes=10))
    with github_auth._cache_lock:
        github_auth._token_cache[2222] = {
            "token": "ghs_expiredtoken",
            "expires_at": past_time
        }
        
    mock_response = MagicMock()
    mock_response.status_code = 201
    future_time = (datetime.now(timezone.utc) + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    mock_response.json.return_value = {
        "token": "ghs_newtoken",
        "expires_at": future_time
    }
    
    with patch("requests.post", return_value=mock_response) as mock_post:
        token = get_installation_token(2222)
        assert token == "ghs_newtoken"
        mock_post.assert_called_once()


def test_get_installation_token_unauthorized_expired_jwt():
    """Verify that 401 response with expired claim triggers ExpiredJWTError."""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.json.return_value = {
        "message": "'Expiration time' claim ('exp') must be a future time"
    }
    
    with patch("requests.post", return_value=mock_response):
        with pytest.raises(ExpiredJWTError) as exc_info:
            get_installation_token(3333)
        assert "JWT expired" in str(exc_info.value)


def test_get_installation_token_bad_request():
    """Verify that bad request/non-201 response raises InstallationTokenRequestError."""
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.json.return_value = {
        "message": "Invalid request parameters"
    }
    
    with patch("requests.post", return_value=mock_response):
        with pytest.raises(InstallationTokenRequestError) as exc_info:
            get_installation_token(3333)
        assert "Failed to request installation token" in str(exc_info.value)


def test_get_installation_token_network_error():
    """Verify that a requests network exception is wrapped in GitHubAPIError."""
    with patch("requests.post", side_effect=requests.RequestException("Connection refused")):
        with pytest.raises(GitHubAPIError) as exc_info:
            get_installation_token(3333)
        assert "Network error" in str(exc_info.value)


def test_get_installation_info_success():
    """Verify get_installation_info retrieves installation details from GitHub."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    info_payload = {
        "id": 55555,
        "account": {"login": "octocat"},
        "repository_selection": "all"
    }
    mock_response.json.return_value = info_payload
    
    with patch("requests.get", return_value=mock_response) as mock_get:
        info = get_installation_info(55555)
        assert info["id"] == 55555
        assert info["account"]["login"] == "octocat"
        mock_get.assert_called_once_with(
            "https://api.github.com/app/installations/55555",
            headers=ANY,
            timeout=10
        )


def test_get_installation_info_not_found():
    """Verify 404 response on get_installation_info raises GitHubAPIError."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.json.return_value = {"message": "Not Found"}
    
    with patch("requests.get", return_value=mock_response):
        with pytest.raises(GitHubAPIError) as exc_info:
            get_installation_info(99999)
        assert "not found" in str(exc_info.value).lower()


def test_authenticated_github_client():
    """Verify that authenticated_github_client returns a Github object."""
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "token": "ghs_clienttoken",
        "expires_at": "2026-07-16T16:32:00Z"
    }
    
    with patch("requests.post", return_value=mock_response):
        client = authenticated_github_client(12345)
        from github import Github
        assert isinstance(client, Github)


def test_save_and_load_installation_id():
    """Verify that installation ID is saved securely and loaded correctly."""
    from src.github_auth import INSTALLATION_FILE
    
    # Ensure any existing file is backed up or removed
    existed = INSTALLATION_FILE.exists()
    old_content = None
    if existed:
        old_content = INSTALLATION_FILE.read_text(encoding="utf-8")
        INSTALLATION_FILE.unlink()
        
    try:
        save_installation_id(98765)
        loaded = load_installation_id()
        assert loaded == 98765
        
        # Verify file permissions on Unix-like systems (mode 600)
        if os.name != 'nt':
            stat_info = os.stat(INSTALLATION_FILE)
            # Permission bits: stat_info.st_mode & 0o777 should be 0o600
            assert (stat_info.st_mode & 0o777) == 0o600
    finally:
        # Clean up
        if INSTALLATION_FILE.exists():
            INSTALLATION_FILE.unlink()
        if existed and old_content is not None:
            INSTALLATION_FILE.write_text(old_content, encoding="utf-8")


def test_load_installation_id_missing():
    """Verify load_installation_id returns None when the config file does not exist."""
    from src.github_auth import INSTALLATION_FILE
    existed = INSTALLATION_FILE.exists()
    old_content = None
    if existed:
        old_content = INSTALLATION_FILE.read_text(encoding="utf-8")
        INSTALLATION_FILE.unlink()
        
    try:
        assert load_installation_id() is None
    finally:
        if existed and old_content is not None:
            INSTALLATION_FILE.write_text(old_content, encoding="utf-8")


def test_get_app_info_success():
    """Verify get_app_info fetches app info correctly."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": 12345,
        "slug": "rover-app",
        "html_url": "https://github.com/apps/rover-app"
    }
    
    with patch("requests.get", return_value=mock_response):
        info = get_app_info()
        assert info["id"] == 12345
        assert info["slug"] == "rover-app"
        assert info["html_url"] == "https://github.com/apps/rover-app"


def test_get_app_info_unauthorized():
    """Verify get_app_info raises ExpiredJWTError on 401 expiration response."""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.json.return_value = {"message": "JWT expired"}
    
    with patch("requests.get", return_value=mock_response):
        with pytest.raises(ExpiredJWTError) as exc_info:
            get_app_info()
        assert "JWT expired" in str(exc_info.value)


def test_get_app_info_failure():
    """Verify get_app_info raises GitHubAPIError on generic API error."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    
    with patch("requests.get", return_value=mock_response):
        with pytest.raises(GitHubAPIError) as exc_info:
            get_app_info()
        assert "GitHub API returned error" in str(exc_info.value)


def test_list_installation_repositories_success():
    """Verify list_installation_repositories returns repositories list."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "repositories": [
            {"id": 1, "full_name": "owner/repo1"},
            {"id": 2, "full_name": "owner/repo2"}
        ]
    }
    
    with patch("src.github_auth.get_installation_token", return_value="mock_token"):
        with patch("requests.get", return_value=mock_response):
            repos = list_installation_repositories(12345)
            assert len(repos) == 2
            assert repos[0]["full_name"] == "owner/repo1"
            assert repos[1]["full_name"] == "owner/repo2"


def test_list_installation_repositories_unauthorized():
    """Verify list_installation_repositories raises GitHubAPIError on token invalidation."""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.json.return_value = {"message": "Bad credentials"}
    
    with patch("src.github_auth.get_installation_token", return_value="mock_token"):
        with patch("requests.get", return_value=mock_response):
            with pytest.raises(GitHubAPIError) as exc_info:
                list_installation_repositories(12345)
            assert "Unauthorized access token" in str(exc_info.value)


def test_check_repository_access_success():
    """Verify check_repository_access returns True if response is 200."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    
    with patch("src.github_auth.get_installation_token", return_value="mock_token"):
        with patch("requests.get", return_value=mock_response):
            assert check_repository_access(12345, "owner/repo") is True


def test_check_repository_access_denied():
    """Verify check_repository_access returns False if status is not 200."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    
    with patch("src.github_auth.get_installation_token", return_value="mock_token"):
        with patch("requests.get", return_value=mock_response):
            assert check_repository_access(12345, "owner/repo") is False


def test_check_repository_access_exception():
    """Verify check_repository_access returns False on request exception."""
    with patch("src.github_auth.get_installation_token", return_value="mock_token"):
        with patch("requests.get", side_effect=requests.RequestException("Timeout")):
            assert check_repository_access(12345, "owner/repo") is False

