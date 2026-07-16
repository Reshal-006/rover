"""
github_auth.py — GitHub App authentication foundation module for Rover.
"""

import os
import time
import json
import logging
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv
import jwt
import requests
from github import Github

# Setup module-level logger
logger = logging.getLogger("rover.github_auth")

# Ensure we load the repo-root .env
load_dotenv(Path(__file__).resolve().parent.parent / '.env')

# Load raw environment variables
GITHUB_APP_ID = os.getenv('GITHUB_APP_ID', '').strip()
GITHUB_PRIVATE_KEY = os.getenv('GITHUB_PRIVATE_KEY', '').strip()
GITHUB_WEBHOOK_SECRET = os.getenv('GITHUB_WEBHOOK_SECRET', '').strip()
GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID', '').strip()
GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET', '').strip()

# In-memory thread-safe cache for installation tokens
# Format: installation_id -> {"token": str, "expires_at": datetime (timezone.utc)}
_token_cache = {}
_cache_lock = threading.Lock()


def clear_token_cache():
    """Clears the in-memory token cache to force a refresh on next call."""
    with _cache_lock:
        _token_cache.clear()
        logger.info("Cleared installation token cache.")


class GitHubAppAuthError(Exception):
    """Base exception for all GitHub App authentication errors."""
    pass


class InvalidAppConfigError(GitHubAppAuthError):
    """Raised when GITHUB_APP_ID is missing or invalid."""
    pass


class InvalidPrivateKeyError(GitHubAppAuthError):
    """Raised when GITHUB_PRIVATE_KEY is missing, malformed, or references a missing file."""
    pass


class JWTGenerationError(GitHubAppAuthError):
    """Raised when JWT generation fails."""
    pass


class InstallationTokenRequestError(GitHubAppAuthError):
    """Raised when token exchange with GitHub fails."""
    pass


class ExpiredJWTError(GitHubAppAuthError):
    """Raised when JWT has expired or is rejected as expired by GitHub."""
    pass


class GitHubAPIError(GitHubAppAuthError):
    """Raised when a generic GitHub API request fails."""
    pass


def _load_private_key(key_setting: str) -> str:
    """
    Loads and validates the private key from the environment setting.
    The setting can be either a path to a PEM file or the raw PEM content string.
    """
    if not key_setting:
        raise InvalidPrivateKeyError("GITHUB_PRIVATE_KEY is empty or not set.")

    # 1. Check if it points to an existing file
    if os.path.exists(key_setting):
        try:
            with open(key_setting, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                logger.debug("Loaded private key from file path: %s", key_setting)
                return content
        except Exception as e:
            raise InvalidPrivateKeyError(f"Failed to read private key file '{key_setting}': {e}")

    # 2. Treat as raw PEM content
    # Support escaped newlines (e.g. \n or \\n) commonly used in env variables
    key_content = key_setting.replace('\\n', '\n').replace('\n\n', '\n').strip()

    if not (key_content.startswith("-----BEGIN") and "-----END" in key_content):
        raise InvalidPrivateKeyError(
            "GITHUB_PRIVATE_KEY is neither a valid file path nor a valid PEM formatted string."
        )

    logger.debug("Loaded private key from raw string content.")
    return key_content


def _parse_iso_datetime(dt_str: str) -> datetime:
    """
    Parses an ISO 8601 UTC datetime string (e.g. 2016-07-11T22:14:10Z) into a timezone-aware datetime object.
    """
    # Replace 'Z' with '+00:00' to make it compatible with fromisoformat in older Python versions
    normalized = dt_str.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def create_app_jwt() -> str:
    """
    Generates a signed JWT using the GITHUB_APP_ID and GITHUB_PRIVATE_KEY.
    Raises:
        InvalidAppConfigError: if GITHUB_APP_ID is missing or not an integer.
        InvalidPrivateKeyError: if the private key fails validation.
        JWTGenerationError: if JWT encoding fails.
    """
    app_id = GITHUB_APP_ID
    if not app_id:
        raise InvalidAppConfigError("GITHUB_APP_ID is not configured in the environment.")

    try:
        app_id_int = int(app_id)
    except ValueError:
        raise InvalidAppConfigError(f"GITHUB_APP_ID must be a numeric integer, got: '{app_id}'")

    raw_key = GITHUB_PRIVATE_KEY
    pem_key = _load_private_key(raw_key)

    now = int(time.time())
    payload = {
        # Issued 60 seconds in the past to allow for clock drift between server & GitHub
        "iat": now - 60,
        # Expire in 10 minutes (maximum allowed by GitHub)
        "exp": now + 600 - 60,
        # Issuer is the GitHub App ID
        "iss": str(app_id_int)
    }

    try:
        token = jwt.encode(payload, pem_key, algorithm="RS256")
        if isinstance(token, bytes):
            token = token.decode("utf-8")
        logger.debug("Successfully generated new App JWT.")
        return token
    except Exception as e:
        raise JWTGenerationError(f"Failed to generate and sign JWT: {e}")


def get_installation_token(installation_id: int) -> str:
    """
    Retrieves the installation access token for a given installation_id.
    Uses in-memory caching and automatically refreshes tokens that are expired or expiring in < 60 seconds.

    Raises:
        ExpiredJWTError: if the JWT is expired or rejected as expired.
        InstallationTokenRequestError: if GitHub rejects the token request.
        GitHubAPIError: on network or API failures.
    """
    now = datetime.now(timezone.utc)

    # Check cache first
    with _cache_lock:
        cached = _token_cache.get(installation_id)
        if cached:
            # If the token is valid and has more than 60 seconds remaining, reuse it
            if cached["expires_at"] - now > timedelta(seconds=60):
                logger.debug("Using cached installation token for installation %s.", installation_id)
                return cached["token"]
            logger.info("Cached token for installation %s is expired or expiring soon. Refreshing...", installation_id)

    # Cache miss or expired: Generate JWT and request new token
    jwt_token = create_app_jwt()

    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    try:
        response = requests.post(url, headers=headers, timeout=10)
    except requests.RequestException as e:
        raise GitHubAPIError(f"Network error while requesting installation token: {e}")

    if response.status_code != 201:
        try:
            err_data = response.json()
            msg = err_data.get("message", "")
        except Exception:
            msg = response.text

        logger.error(
            "Failed to obtain installation token for installation %s: %s (status: %s)",
            installation_id, msg, response.status_code
        )

        if response.status_code == 401:
            if "expiration" in msg.lower() or "exp" in msg.lower() or "jwt" in msg.lower():
                raise ExpiredJWTError(f"JWT expired or invalid: {msg}")
            raise JWTGenerationError(f"Unauthorized (invalid JWT/App credentials): {msg}")

        raise InstallationTokenRequestError(
            f"Failed to request installation token (status {response.status_code}): {msg}"
        )

    try:
        res_data = response.json()
        token = res_data["token"]
        expires_at_str = res_data["expires_at"]
        expires_at = _parse_iso_datetime(expires_at_str)
    except (KeyError, ValueError) as e:
        raise InstallationTokenRequestError(f"Failed to parse installation token response: {e}")

    with _cache_lock:
        _token_cache[installation_id] = {
            "token": token,
            "expires_at": expires_at
        }

    logger.info("Successfully fetched and cached new installation token for installation %s.", installation_id)
    return token


def get_installation_info(installation_id: int) -> dict:
    """
    Queries details about a specific installation. Requires App JWT authentication.

    Raises:
        ExpiredJWTError: if the JWT is expired or rejected as expired.
        GitHubAPIError: if the installation is not found or API request fails.
    """
    jwt_token = create_app_jwt()
    url = f"https://api.github.com/app/installations/{installation_id}"
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
    except requests.RequestException as e:
        raise GitHubAPIError(f"Network error while retrieving installation info: {e}")

    if response.status_code != 200:
        try:
            err_data = response.json()
            msg = err_data.get("message", "")
        except Exception:
            msg = response.text

        logger.error(
            "Failed to fetch installation info for installation %s: %s (status: %s)",
            installation_id, msg, response.status_code
        )

        if response.status_code == 401:
            if "expiration" in msg.lower() or "exp" in msg.lower() or "jwt" in msg.lower():
                raise ExpiredJWTError(f"JWT expired or invalid: {msg}")
            raise JWTGenerationError(f"Unauthorized (invalid JWT/App credentials): {msg}")

        if response.status_code == 404:
            raise GitHubAPIError(f"Installation ID {installation_id} not found: {msg}")

        raise GitHubAPIError(f"GitHub API returned error (status {response.status_code}): {msg}")

    try:
        return response.json()
    except ValueError as e:
        raise GitHubAPIError(f"Failed to parse installation info response: {e}")


def authenticated_github_client(installation_id: int) -> Github:
    """
    Returns an authenticated PyGithub client instance for the specified installation ID.
    Automatically fetches/renews the installation token.
    """
    token = get_installation_token(installation_id)
    try:
        from github import Auth
        auth = Auth.Token(token)
        return Github(auth=auth)
    except (ImportError, AttributeError):
        return Github(token)


# File path for saving the GitHub App Installation ID securely
INSTALLATION_FILE = Path(__file__).resolve().parent.parent / "scans" / "github_app_installation.json"


def save_installation_id(installation_id: int):
    """
    Saves the GitHub App Installation ID securely to a local file.
    Restricts file permissions so only the owner can read/write it.
    """
    INSTALLATION_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Create/truncate file and write data
        with open(INSTALLATION_FILE, "w", encoding="utf-8") as f:
            json.dump({"installation_id": installation_id}, f)
        
        # Set file permissions to owner read/write only (600)
        os.chmod(INSTALLATION_FILE, 0o600)
        logger.info("Successfully saved Installation ID %s securely.", installation_id)
    except Exception as e:
        logger.error("Failed to securely save Installation ID %s: %s", installation_id, e)
        raise GitHubAppAuthError(f"Secure save failed for installation ID: {e}")


def load_installation_id() -> int | None:
    """
    Loads the saved GitHub App Installation ID from the local secure file.
    Returns None if the file does not exist or cannot be read.
    """
    if not INSTALLATION_FILE.exists():
        logger.debug("No installation ID file found at %s", INSTALLATION_FILE)
        return None
    try:
        with open(INSTALLATION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            inst_id = data.get("installation_id")
            if inst_id is not None:
                return int(inst_id)
    except Exception as e:
        logger.warning("Failed to load Installation ID: %s", e)
    return None


def get_app_info() -> dict:
    """
    Queries details about the GitHub App (slug, html_url, etc.) using JWT auth.

    Raises:
        ExpiredJWTError: if the JWT has expired.
        GitHubAPIError: on failure.
    """
    jwt_token = create_app_jwt()
    url = "https://api.github.com/app"
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
    except requests.RequestException as e:
        raise GitHubAPIError(f"Network error while retrieving App info: {e}")

    if response.status_code != 200:
        try:
            err_data = response.json()
            msg = err_data.get("message", "")
        except Exception:
            msg = response.text

        logger.error("Failed to fetch App info: %s (status: %s)", msg, response.status_code)
        
        if response.status_code == 401:
            if "expiration" in msg.lower() or "exp" in msg.lower() or "jwt" in msg.lower():
                raise ExpiredJWTError(f"JWT expired or invalid: {msg}")
            raise JWTGenerationError(f"Unauthorized (invalid JWT/App credentials): {msg}")

        raise GitHubAPIError(f"GitHub API returned error (status {response.status_code}): {msg}")

    try:
        return response.json()
    except ValueError as e:
        raise GitHubAPIError(f"Failed to parse App info response: {e}")


def list_installation_repositories(installation_id: int) -> list[dict]:
    """
    Lists repositories accessible to the specified installation.
    Uses the installation token.

    Raises:
        ExpiredJWTError: if the installation token fails due to expired JWT.
        GitHubAPIError: on API/network failures.
    """
    token = get_installation_token(installation_id)
    url = "https://api.github.com/installation/repositories"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    logger.info("Fetching accessible repositories for installation %s...", installation_id)

    try:
        response = requests.get(url, headers=headers, timeout=10)
    except requests.RequestException as e:
        raise GitHubAPIError(f"Network error while listing repositories: {e}")

    if response.status_code != 200:
        try:
            err_data = response.json()
            msg = err_data.get("message", "")
        except Exception:
            msg = response.text

        logger.error(
            "Failed to list repositories for installation %s: %s (status: %s)",
            installation_id, msg, response.status_code
        )

        if response.status_code == 401:
            # Token might have expired or revoked
            raise GitHubAPIError(f"Unauthorized access token: {msg}")

        raise GitHubAPIError(f"GitHub API returned error (status {response.status_code}): {msg}")

    try:
        data = response.json()
        repos = data.get("repositories", [])
        logger.info("Successfully fetched %s repositories for installation %s.", len(repos), installation_id)
        return repos
    except ValueError as e:
        raise GitHubAPIError(f"Failed to parse repositories response: {e}")


def check_repository_access(installation_id: int, repo_full_name: str) -> bool:
    """
    Checks if the specified repository belongs to the current installation.
    Performs a fast, O(1) query GET /repos/{repo_full_name}.

    Returns:
        True if the installation has access, False otherwise.
    """
    try:
        token = get_installation_token(installation_id)
    except Exception as e:
        logger.warning("Failed to obtain installation token to check repo access: %s", e)
        return False

    url = f"https://api.github.com/repos/{repo_full_name}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    logger.debug("Checking repository access for %s on installation %s...", repo_full_name, installation_id)

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            logger.info("Access confirmed for repository %s.", repo_full_name)
            return True
        logger.warning(
            "Access denied/Not found for repository %s (status: %s)",
            repo_full_name, response.status_code
        )
        return False
    except Exception as e:
        logger.error("Exception checking repository access for %s: %s", repo_full_name, e)
        return False
