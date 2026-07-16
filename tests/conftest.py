import pytest
import os

@pytest.fixture(autouse=True)
def isolate_test_env(monkeypatch):
    """
    Ensure all tests run with a clean env isolated from the active .env variables
    unless they explicitly set them in the test body.
    """
    # Disable GitHub App by default in tests
    monkeypatch.setenv("USE_GITHUB_APP", "false")
    monkeypatch.delenv("GITHUB_INSTALLATION_ID", raising=False)
