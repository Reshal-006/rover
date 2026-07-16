import os
import sys
import pytest
from unittest.mock import MagicMock, patch, ANY
from github import GithubException, Github

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.github_client import (
    get_github_client,
    RepositoryContext,
    create_issue,
    read_issue,
    post_comment,
    create_branch,
    open_pull_request,
    update_file,
    download_file,
    read_repository,
    get_git_tree,
    read_blob_content,
    clone_repo,
    push_commits,
    GitHubClientError,
    RepositoryNotInstalled,
    RepositoryAccessDenied,
    AuthenticationFailed,
    BranchCreationFailed,
    PullRequestFailed,
    IssueCreationFailed
)


def test_factory_pat_fallback(monkeypatch):
    """Verify that get_github_client falls back to PAT when USE_GITHUB_APP is false."""
    monkeypatch.setenv("USE_GITHUB_APP", "false")
    monkeypatch.setenv("GITHUB_TOKEN", "mock_pat_token")
    
    client = get_github_client()
    assert isinstance(client, Github)


def test_factory_app_missing_install(monkeypatch):
    """Verify get_github_client raises RepositoryNotInstalled if app auth is true but no ID is stored."""
    monkeypatch.setenv("USE_GITHUB_APP", "true")
    
    with patch("src.github_client.load_installation_id", return_value=None):
        with pytest.raises(RepositoryNotInstalled):
            get_github_client()


def test_factory_app_success(monkeypatch):
    """Verify get_github_client uses authenticated_github_client when app auth is true."""
    monkeypatch.setenv("USE_GITHUB_APP", "true")
    
    mock_client = MagicMock(spec=Github)
    with patch("src.github_client.load_installation_id", return_value=12345):
        with patch("src.github_client.authenticated_github_client", return_value=mock_client) as mock_auth:
            client = get_github_client()
            assert client == mock_client
            mock_auth.assert_called_once_with(12345)


def test_repository_context_init():
    """Verify RepositoryContext initializes with owner, repo, and default branch."""
    mock_client = MagicMock(spec=Github)
    mock_repo = MagicMock()
    mock_repo.default_branch = "develop"
    mock_client.get_repo.return_value = mock_repo
    
    with patch("src.github_client.get_github_client", return_value=mock_client):
        ctx = RepositoryContext("owner-name", "repo-name", 999)
        assert ctx.owner == "owner-name"
        assert ctx.repo == "repo-name"
        assert ctx.installation_id == 999
        assert ctx.default_branch == "develop"


def test_retry_on_auth_failure():
    """Verify decorator clears token cache and retries once on 401/403 authentication failure."""
    mock_client1 = MagicMock(spec=Github)
    mock_client2 = MagicMock(spec=Github)
    
    # First client raises 401 Unauthorized
    mock_repo1 = MagicMock()
    mock_repo1.create_issue.side_effect = GithubException(401, {"message": "Bad credentials"}, None)
    mock_client1.get_repo.return_value = mock_repo1
    
    # Second client succeeds
    mock_repo2 = MagicMock()
    mock_issue = MagicMock()
    mock_issue.number = 42
    mock_repo2.create_issue.return_value = mock_issue
    mock_client2.get_repo.return_value = mock_repo2
    
    ctx = MagicMock()
    ctx.owner = "owner"
    ctx.repo = "repo"
    ctx.installation_id = 12345
    ctx.client = mock_client1
    
    # We patch get_github_client to return the second client on retry
    with patch("src.github_client.get_github_client", return_value=mock_client2):
        with patch("src.github_auth.clear_token_cache") as mock_clear:
            issue_num = create_issue(ctx, "Title", "Body")
            assert issue_num == 42
            mock_clear.assert_called_once()
            # Verify the context client was updated to the fresh client
            assert ctx.client == mock_client2


def test_custom_exception_mapping(monkeypatch):
    """Verify GithubExceptions are correctly mapped to our custom exceptions."""
    mock_client = MagicMock(spec=Github)
    monkeypatch.setattr("src.github_client.get_github_client", lambda inst_id: mock_client)
    monkeypatch.setattr("src.github_client.get_installation_token", lambda inst_id: "fake_token")
    
    ctx = MagicMock()
    ctx.client = mock_client
    ctx.owner = "owner"
    ctx.repo = "repo"
    ctx.installation_id = 12345
    
    # 404 -> RepositoryAccessDenied
    mock_client.get_repo.side_effect = GithubException(404, {"message": "Not Found"}, None)
    with pytest.raises(RepositoryAccessDenied):
        read_repository(ctx)
        
    # 403 Rate Limit -> GitHubClientError
    mock_client.get_repo.side_effect = [
        GithubException(403, {"message": "rate limit exceeded"}, None),
        GithubException(403, {"message": "rate limit exceeded"}, None)
    ]
    with pytest.raises(GitHubClientError) as exc_info:
        read_repository(ctx)
    assert "Rate limit exceeded" in str(exc_info.value)
    
    # 403 Access Denied -> RepositoryAccessDenied
    mock_client.get_repo.side_effect = [
        GithubException(403, {"message": "Forbidden"}, None),
        GithubException(403, {"message": "Forbidden"}, None)
    ]
    with pytest.raises(RepositoryAccessDenied):
        read_repository(ctx)


def test_create_issue_success():
    """Verify create_issue wrapper successfully creates an issue."""
    mock_client = MagicMock(spec=Github)
    mock_repo = MagicMock()
    mock_issue = MagicMock()
    mock_issue.number = 101
    mock_repo.create_issue.return_value = mock_issue
    mock_client.get_repo.return_value = mock_repo
    
    ctx = MagicMock()
    ctx.client = mock_client
    ctx.owner = "owner"
    ctx.repo = "repo"
    ctx.installation_id = 12345
    
    number = create_issue(ctx, "Issue Title", "Description", ["bug"])
    assert number == 101
    mock_repo.create_issue.assert_called_once_with(title="Issue Title", body="Description", labels=["bug"])


def test_open_pull_request_success():
    """Verify open_pull_request wrapper successfully opens a pull request."""
    mock_client = MagicMock(spec=Github)
    mock_repo = MagicMock()
    mock_pr = MagicMock()
    mock_pr.number = 202
    mock_repo.create_pull.return_value = mock_pr
    mock_client.get_repo.return_value = mock_repo
    
    ctx = MagicMock()
    ctx.client = mock_client
    ctx.owner = "owner"
    ctx.repo = "repo"
    ctx.installation_id = 12345
    ctx.default_branch = "main"
    
    number = open_pull_request(ctx, "PR Title", "PR Body", "feature", "main")
    assert number == 202
    mock_repo.create_pull.assert_called_once_with(title="PR Title", body="PR Body", head="feature", base="main")


def test_create_branch_success():
    """Verify create_branch wrapper successfully creates a Git ref."""
    mock_client = MagicMock(spec=Github)
    mock_repo = MagicMock()
    mock_ref = MagicMock()
    mock_ref.object.sha = "abcdef12345"
    mock_repo.get_git_ref.return_value = mock_ref
    mock_client.get_repo.return_value = mock_repo
    
    ctx = MagicMock()
    ctx.client = mock_client
    ctx.owner = "owner"
    ctx.repo = "repo"
    ctx.installation_id = 12345
    ctx.default_branch = "main"
    
    create_branch(ctx, "new-feature", "main")
    mock_repo.get_git_ref.assert_called_once_with("heads/main")
    mock_repo.create_git_ref.assert_called_once_with(ref="refs/heads/new-feature", sha="abcdef12345")
