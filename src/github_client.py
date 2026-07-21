"""github_client.py — all GitHub API interactions for Rover.
"""
import os
import subprocess
import logging
import functools
import time
from pathlib import Path
from dotenv import load_dotenv
from github import Github, GithubException
from src.github_auth import load_installation_id, get_installation_token, authenticated_github_client

logger = logging.getLogger("rover.github_client")

# Ensure we load the repo-root .env
load_dotenv(Path(__file__).resolve().parent.parent / '.env')


# --- Custom GitHub Exceptions ---

class GitHubClientError(Exception):
    """Base exception for all GitHub Client operations."""
    pass

class RepositoryNotInstalled(GitHubClientError):
    """Raised when the GitHub App is not installed on the repository's account."""
    pass

class InstallationExpired(GitHubClientError):
    """Raised when the installation token has expired or is invalid."""
    pass

class RepositoryAccessDenied(GitHubClientError):
    """Raised when access to a specific repository is denied."""
    pass

class AuthenticationFailed(GitHubClientError):
    """Raised when authentication fails (missing PAT or App credentials)."""
    pass

class BranchCreationFailed(GitHubClientError):
    """Raised when creating a branch fails."""
    pass

class PullRequestFailed(GitHubClientError):
    """Raised when opening a pull request fails."""
    pass

class IssueCreationFailed(GitHubClientError):
    """Raised when creating an issue fails."""
    pass


# --- Client Factory ---

def get_github_client(installation_id: int | None = None) -> Github:
    """
    Returns a PyGithub client instance using centralized authentication.
    App Authentication is preferred if USE_GITHUB_APP=true, falling back to PAT.
    """
    USE_GITHUB_APP = os.getenv("USE_GITHUB_APP", "false").lower() == "true"
    if USE_GITHUB_APP:
        if not installation_id:
            installation_id = load_installation_id()
        if installation_id:
            try:
                return authenticated_github_client(installation_id)
            except Exception as e:
                logger.warning("GitHub App authentication failed for installation %s: %s. Falling back to PAT token...", installation_id, e)

    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        try:
            from github import Auth
            auth = Auth.Token(token)
            return Github(auth=auth)
        except (ImportError, AttributeError):
            return Github(token)
            
    raise RepositoryNotInstalled("No valid GitHub App installation or GITHUB_TOKEN configured.")


# --- Repository Context ---

class RepositoryContext:
    """
    Wraps the repository identity and encapsulates the authenticated client/metadata context.
    """
    def __init__(self, owner: str, repo: str, installation_id: int | None = None):
        self.owner = owner.strip()
        self.repo = repo.strip()
        self.installation_id = installation_id
        self.client = get_github_client(self.installation_id)
        
        # Determine default branch
        try:
            repo_obj = self.client.get_repo(f"{self.owner}/{self.repo}")
            self.default_branch = repo_obj.default_branch
        except Exception as e:
            logger.warning("Failed to fetch default branch for %s/%s: %s. Defaulting to 'main'.", self.owner, self.repo, e)
            self.default_branch = "main"

    @classmethod
    def from_repo_name(cls, repo_name: str, installation_id: int | None = None):
        repo_name = repo_name.strip()
        if "/" in repo_name:
            owner, repo = repo_name.split("/", 1)
        else:
            owner, repo = "", repo_name
        return cls(owner, repo, installation_id)


# --- Helper Exception Mapper & Retry Decorator ---

def _handle_github_exception(e: GithubException):
    status = e.status
    msg = e.data.get("message", "") if isinstance(e.data, dict) else str(e)
    
    logger.error("GitHub API Error (status %s): %s", status, msg)
    
    if status == 401:
        raise AuthenticationFailed(f"Authentication failed: {msg}")
    elif status == 403:
        if "rate limit" in msg.lower():
            logger.error("GitHub Rate Limit exceeded.")
            raise GitHubClientError(f"Rate limit exceeded: {msg}")
        raise RepositoryAccessDenied(f"Access denied: {msg}")
    elif status == 404:
        raise RepositoryAccessDenied(f"Repository not found or access denied: {msg}")
    elif "pull request" in msg.lower() or "pr" in msg.lower():
        raise PullRequestFailed(f"Pull Request operation failed: {msg}")
    elif "branch" in msg.lower() or "ref" in msg.lower():
        raise BranchCreationFailed(f"Branch operation failed: {msg}")
    elif "issue" in msg.lower():
        raise IssueCreationFailed(f"Issue operation failed: {msg}")
    else:
        raise GitHubClientError(f"GitHub operation failed (status {status}): {msg}")

def _handle_generic_exception(e: Exception):
    logger.error("Unexpected error during GitHub operation: %s", e)
    raise GitHubClientError(f"Unexpected error: {e}")


def with_github_retry(func):
    """
    Decorator that catches expired token/auth issues, clears token cache,
    refreshes the client in RepositoryContext, and retries the operation once.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except GithubException as e:
            if e.status in (401, 403):
                logger.warning("GitHub authentication failure (status %s). Retrying once with a fresh token...", e.status)
                from src.github_auth import clear_token_cache
                clear_token_cache()
                
                # If first arg has 'client' attribute, refresh it
                if args and hasattr(args[0], "client"):
                    ctx = args[0]
                    inst_id = getattr(ctx, "installation_id", None)
                    ctx.client = get_github_client(inst_id)
                
                try:
                    return func(*args, **kwargs)
                except GithubException as renewed_e:
                    _handle_github_exception(renewed_e)
            else:
                _handle_github_exception(e)
        except Exception as e:
            _handle_generic_exception(e)
    return wrapper


# --- GitHub Operation Wrappers ---

@with_github_retry
def create_issue(ctx: RepositoryContext, title: str, body: str, labels: list[str] = None) -> int:
    auth_method = "GitHub App" if os.getenv("USE_GITHUB_APP", "false").lower() == "true" else "PAT"
    logger.info(
        "Creating issue | Auth: %s | Installation: %s | Repo: %s/%s | Title: %s",
        auth_method, ctx.installation_id, ctx.owner, ctx.repo, title
    )
    repo = ctx.client.get_repo(f"{ctx.owner}/{ctx.repo}")
    issue = repo.create_issue(title=title, body=body, labels=labels or [])
    logger.info("Created Issue #%s", issue.number)
    return issue.number


@with_github_retry
def read_issue(ctx: RepositoryContext, issue_number: int) -> dict:
    auth_method = "GitHub App" if os.getenv("USE_GITHUB_APP", "false").lower() == "true" else "PAT"
    logger.info(
        "Reading issue | Auth: %s | Installation: %s | Repo: %s/%s | Issue Number: %s",
        auth_method, ctx.installation_id, ctx.owner, ctx.repo, issue_number
    )
    repo = ctx.client.get_repo(f"{ctx.owner}/{ctx.repo}")
    issue = repo.get_issue(issue_number)
    return {
        "number": issue.number,
        "title": issue.title,
        "body": issue.body,
        "labels": [label.name for label in issue.labels],
        "state": issue.state
    }


@with_github_retry
def post_comment(ctx: RepositoryContext, issue_number: int, body: str) -> int:
    auth_method = "GitHub App" if os.getenv("USE_GITHUB_APP", "false").lower() == "true" else "PAT"
    logger.info(
        "Posting comment | Auth: %s | Installation: %s | Repo: %s/%s | Issue Number: %s",
        auth_method, ctx.installation_id, ctx.owner, ctx.repo, issue_number
    )
    repo = ctx.client.get_repo(f"{ctx.owner}/{ctx.repo}")
    issue = repo.get_issue(issue_number)
    comment = issue.create_comment(body)
    logger.info("Posted Comment ID %s", comment.id)
    return comment.id


@with_github_retry
def create_branch(ctx: RepositoryContext, branch_name: str, base_branch: str = None):
    auth_method = "GitHub App" if os.getenv("USE_GITHUB_APP", "false").lower() == "true" else "PAT"
    base = base_branch or ctx.default_branch
    logger.info(
        "Creating branch | Auth: %s | Installation: %s | Repo: %s/%s | Branch: %s | Base: %s",
        auth_method, ctx.installation_id, ctx.owner, ctx.repo, branch_name, base
    )
    repo = ctx.client.get_repo(f"{ctx.owner}/{ctx.repo}")
    base_ref = repo.get_git_ref(f"heads/{base}")
    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_ref.object.sha)
    logger.info("Successfully created branch %s", branch_name)


@with_github_retry
def read_repository(ctx: RepositoryContext) -> dict:
    auth_method = "GitHub App" if os.getenv("USE_GITHUB_APP", "false").lower() == "true" else "PAT"
    logger.info(
        "Reading repository | Auth: %s | Installation: %s | Repo: %s/%s",
        auth_method, ctx.installation_id, ctx.owner, ctx.repo
    )
    repo = ctx.client.get_repo(f"{ctx.owner}/{ctx.repo}")
    return {
        "name": repo.name,
        "full_name": repo.full_name,
        "description": repo.description,
        "default_branch": repo.default_branch,
        "private": repo.private
    }


def clone_repo(ctx_or_name, workspace_dir: str | None = None):
    """
    Clones the repository defined in context into an isolated workspace directory.
    Accepts either RepositoryContext or a repo_name string.
    """
    from src.github_auth import sanitize_text
    if isinstance(ctx_or_name, RepositoryContext):
        ctx = ctx_or_name
    else:
        inst_id = load_installation_id()
        ctx = RepositoryContext.from_repo_name(ctx_or_name, inst_id)
        
    if not workspace_dir:
        workspace_dir = f"workspaces/{ctx.owner}_{ctx.repo}"

    USE_GITHUB_APP = os.getenv('USE_GITHUB_APP', 'false').lower() == 'true'
    auth_method = "GitHub App" if USE_GITHUB_APP else "PAT"
    logger.info(
        "Cloning repository | Auth: %s | Installation: %s | Repo: %s/%s | Destination: %s",
        auth_method, ctx.installation_id, ctx.owner, ctx.repo, workspace_dir
    )
    
    if USE_GITHUB_APP:
        if not ctx.installation_id:
            raise RepositoryNotInstalled("No installation ID provided for cloning under GitHub App auth.")
        try:
            token = get_installation_token(ctx.installation_id)
        except Exception as e:
            raise AuthenticationFailed(f"Failed to retrieve installation token for App cloning: {e}")
        url = f'https://x-access-token:{token}@github.com/{ctx.owner}/{ctx.repo}.git'
    else:
        token = os.getenv("GITHUB_TOKEN", "").strip()
        if not token:
            raise AuthenticationFailed('GITHUB_TOKEN is not set. Cannot clone repository.')
        url = f'https://{token}@github.com/{ctx.owner}/{ctx.repo}.git'

    os.makedirs(os.path.dirname(os.path.abspath(workspace_dir)), exist_ok=True)

    if os.path.exists(workspace_dir) and os.path.exists(os.path.join(workspace_dir, '.git')):
        if USE_GITHUB_APP:
            try:
                subprocess.run(['git', 'remote', 'set-url', 'origin', url], cwd=workspace_dir, check=True)
                logger.debug("Successfully updated origin remote URL in workspace.")
            except Exception as e:
                logger.warning("Failed to update remote URL in workspace: %s", sanitize_text(str(e)))
        logger.info("Running git pull in existing workspace %s...", workspace_dir)
        subprocess.run(['git', 'pull'], cwd=workspace_dir, check=False)
    else:
        logger.info("Cloning repository into %s...", workspace_dir)
        subprocess.run(['git', 'clone', url, workspace_dir], check=True)


def push_commits(ctx: RepositoryContext, branch_name: str, workspace_dir: str | None = None):
    """
    Pushes local branch changes from workspace_dir to remote origin.
    """
    from src.github_auth import sanitize_text
    if not workspace_dir:
        workspace_dir = f"workspaces/{ctx.owner}_{ctx.repo}"

    USE_GITHUB_APP = os.getenv('USE_GITHUB_APP', 'false').lower() == 'true'
    auth_method = "GitHub App" if USE_GITHUB_APP else "PAT"
    logger.info(
        "Pushing commits | Auth: %s | Installation: %s | Repo: %s/%s | Branch: %s | Dir: %s",
        auth_method, ctx.installation_id, ctx.owner, ctx.repo, branch_name, workspace_dir
    )
    
    if USE_GITHUB_APP:
        if not ctx.installation_id:
            raise RepositoryNotInstalled("No installation ID provided for pushing under GitHub App auth.")
        try:
            token = get_installation_token(ctx.installation_id)
        except Exception as e:
            raise AuthenticationFailed(f"Failed to retrieve installation token for App pushing: {e}")
          
        url = f'https://x-access-token:{token}@github.com/{ctx.owner}/{ctx.repo}.git'
    else:
        token = os.getenv("GITHUB_TOKEN", "").strip()
        if not token:
            raise AuthenticationFailed('GITHUB_TOKEN is not set. Cannot push commits.')
        url = f'https://{token}@github.com/{ctx.owner}/{ctx.repo}.git'

    try:
        subprocess.run(['git', 'remote', 'set-url', 'origin', url], cwd=workspace_dir, check=True)
    except Exception as e:
        logger.warning("Failed to update remote URL: %s", sanitize_text(str(e)))

    res = subprocess.run(['git', 'push', 'origin', branch_name], cwd=workspace_dir, capture_output=True, text=True)
    if res.returncode != 0:
        clean_err = sanitize_text(res.stderr)
        logger.error("Git push failed: %s", clean_err)
        raise GitHubClientError(f"Git push failed: {clean_err}")
    logger.info("Successfully pushed branch %s to origin.", branch_name)


@with_github_retry
def open_pull_request(ctx: RepositoryContext, title: str, body: str, head_branch: str, base_branch: str = None) -> int:
    auth_method = "GitHub App" if os.getenv("USE_GITHUB_APP", "false").lower() == "true" else "PAT"
    base = base_branch or ctx.default_branch
    logger.info(
        "Opening Pull Request | Auth: %s | Installation: %s | Repo: %s/%s | Head Branch: %s | Base Branch: %s",
        auth_method, ctx.installation_id, ctx.owner, ctx.repo, head_branch, base
    )
    repo = ctx.client.get_repo(f"{ctx.owner}/{ctx.repo}")
    pr = repo.create_pull(title=title, body=body, head=head_branch, base=base)
    logger.info("Opened Pull Request #%s", pr.number)
    return pr.number


@with_github_retry
def update_file(ctx: RepositoryContext, filepath: str, message: str, content: str, branch: str = None):
    auth_method = "GitHub App" if os.getenv("USE_GITHUB_APP", "false").lower() == "true" else "PAT"
    target_branch = branch or ctx.default_branch
    logger.info(
        "Updating file | Auth: %s | Installation: %s | Repo: %s/%s | File: %s | Branch: %s",
        auth_method, ctx.installation_id, ctx.owner, ctx.repo, filepath, target_branch
    )
    repo = ctx.client.get_repo(f"{ctx.owner}/{ctx.repo}")
    kwargs = {}
    if branch:
        kwargs["ref"] = branch
    try:
        contents = repo.get_contents(filepath, **kwargs)
        sha = contents.sha
        repo.update_file(path=filepath, message=message, content=content, sha=sha, branch=target_branch)
    except GithubException as e:
        if e.status == 404:
            repo.create_file(path=filepath, message=message, content=content, branch=target_branch)
        else:
            raise
    logger.info("Successfully updated/created file %s", filepath)


@with_github_retry
def fetch_default_branch(ctx: RepositoryContext) -> str:
    auth_method = "GitHub App" if os.getenv("USE_GITHUB_APP", "false").lower() == "true" else "PAT"
    logger.info(
        "Fetching default branch | Auth: %s | Installation: %s | Repo: %s/%s",
        auth_method, ctx.installation_id, ctx.owner, ctx.repo
    )
    repo = ctx.client.get_repo(f"{ctx.owner}/{ctx.repo}")
    return repo.default_branch


@with_github_retry
def get_repository_metadata(ctx: RepositoryContext) -> dict:
    auth_method = "GitHub App" if os.getenv("USE_GITHUB_APP", "false").lower() == "true" else "PAT"
    logger.info(
        "Fetching repository metadata | Auth: %s | Installation: %s | Repo: %s/%s",
        auth_method, ctx.installation_id, ctx.owner, ctx.repo
    )
    repo = ctx.client.get_repo(f"{ctx.owner}/{ctx.repo}")
    return {
        "id": repo.id,
        "owner": repo.owner.login,
        "name": repo.name,
        "full_name": repo.full_name,
        "private": repo.private,
        "html_url": repo.html_url,
        "created_at": repo.created_at.isoformat() if repo.created_at else None,
        "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
    }


@with_github_retry
def get_repository_labels(ctx: RepositoryContext) -> list[str]:
    auth_method = "GitHub App" if os.getenv("USE_GITHUB_APP", "false").lower() == "true" else "PAT"
    logger.info(
        "Fetching repository labels | Auth: %s | Installation: %s | Repo: %s/%s",
        auth_method, ctx.installation_id, ctx.owner, ctx.repo
    )
    repo = ctx.client.get_repo(f"{ctx.owner}/{ctx.repo}")
    return [label.name for label in repo.get_labels()]


@with_github_retry
def download_file(ctx: RepositoryContext, filepath: str, branch: str = None) -> bytes:
    auth_method = "GitHub App" if os.getenv("USE_GITHUB_APP", "false").lower() == "true" else "PAT"
    target_branch = branch or ctx.default_branch
    logger.info(
        "Downloading file | Auth: %s | Installation: %s | Repo: %s/%s | File: %s | Branch: %s",
        auth_method, ctx.installation_id, ctx.owner, ctx.repo, filepath, target_branch
    )
    repo = ctx.client.get_repo(f"{ctx.owner}/{ctx.repo}")
    kwargs = {}
    if branch:
        kwargs["ref"] = branch
    contents = repo.get_contents(filepath, **kwargs)
    if isinstance(contents, list):
        raise GitHubClientError(f"Path '{filepath}' is a directory, not a file.")
    return contents.decoded_content


@with_github_retry
def get_git_tree(ctx: RepositoryContext, sha: str, recursive: bool = False) -> list[dict]:
    auth_method = "GitHub App" if os.getenv("USE_GITHUB_APP", "false").lower() == "true" else "PAT"
    logger.info(
        "Fetching git tree | Auth: %s | Installation: %s | Repo: %s/%s | SHA: %s",
        auth_method, ctx.installation_id, ctx.owner, ctx.repo, sha
    )
    repo = ctx.client.get_repo(f"{ctx.owner}/{ctx.repo}")
    tree = repo.get_git_tree(sha, recursive=recursive)
    return [
        {
            "path": element.path,
            "mode": element.mode,
            "type": element.type,
            "size": element.size,
            "sha": element.sha
        }
        for element in tree.tree
    ]


@with_github_retry
def read_blob_content(ctx: RepositoryContext, blob_sha: str) -> str:
    auth_method = "GitHub App" if os.getenv("USE_GITHUB_APP", "false").lower() == "true" else "PAT"
    logger.info(
        "Reading blob content | Auth: %s | Installation: %s | Repo: %s/%s | SHA: %s",
        auth_method, ctx.installation_id, ctx.owner, ctx.repo, blob_sha
    )
    repo = ctx.client.get_repo(f"{ctx.owner}/{ctx.repo}")
    blob = repo.get_git_blob(blob_sha)
    import base64
    return base64.b64decode(blob.content).decode("utf-8", errors="ignore")


# --- Backwards compatibility wrappers ---

def get_issue_text(ctx_or_name, issue_number: int) -> str:
    if isinstance(ctx_or_name, RepositoryContext):
        ctx = ctx_or_name
    else:
        inst_id = load_installation_id()
        ctx = RepositoryContext.from_repo_name(ctx_or_name, inst_id)
        
    @with_github_retry
    def _get(c: RepositoryContext):
        repo  = c.client.get_repo(f"{c.owner}/{c.repo}")
        issue = repo.get_issue(issue_number)
        return f'Title: {issue.title}\n\n{issue.body or "No description."}'
    return _get(ctx)


def create_issue_from_scan(repository_url: str, bug_id: str, title: str, description: str, installation_id: int | None = None, **kwargs):
    repo_name = repository_url.replace('https://github.com/', '').rstrip('/')
    inst_id = installation_id or load_installation_id()
    ctx = RepositoryContext.from_repo_name(repo_name, inst_id)
    
    @with_github_retry
    def _create(c: RepositoryContext):
        repo = c.client.get_repo(f"{c.owner}/{c.repo}")
        issue = repo.create_issue(
            title=title,
            body=(
                f'Title: {title}\n\n'
                f'Description: {description}\n\n'
                f'Severity: {kwargs.get("severity", "medium")}\n'
                f'Confidence: {kwargs.get("confidence", 0.8)}\n'
                f'Bug ID: {bug_id}\n\n'
                f'Generated by Rover'
            ),
        )
        return issue.number
    return _create(ctx)