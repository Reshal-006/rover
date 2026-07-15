"""github_client.py — all GitHub API interactions for Rover.
"""
from github import Github
import os, subprocess
from pathlib import Path
from dotenv import load_dotenv

# Ensure we load the repo-root .env
load_dotenv(Path(__file__).resolve().parent.parent / '.env')

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '').strip()
if not GITHUB_TOKEN:
    g = None
else:
    g = Github(GITHUB_TOKEN)

def get_issue_text(repo_name: str, issue_number: int) -> str:
    if g is None:
        raise RuntimeError('GITHUB_TOKEN is not set. Set GITHUB_TOKEN in .env or environment to access GitHub APIs.')
    repo  = g.get_repo(repo_name)
    issue = repo.get_issue(issue_number)
    return f'Title: {issue.title}\n\n{issue.body or "No description."}'

def post_comment(repo_name: str, issue_number: int, body: str):
    if g is None:
        raise RuntimeError('GITHUB_TOKEN is not set. Cannot post comments to GitHub. Add a personal access token to .env as GITHUB_TOKEN.')
    repo  = g.get_repo(repo_name)
    issue = repo.get_issue(issue_number)
    issue.create_comment(body)
    print(f'Comment posted on Issue #{issue_number}')

def clone_repo(repo_name: str):
    if os.path.exists('workspace'):
        subprocess.run(['git', 'pull'], cwd='workspace', check=False)
    else:
        if not GITHUB_TOKEN:
            raise RuntimeError('GITHUB_TOKEN is not set. Cannot clone private repos. Add GITHUB_TOKEN to .env.')
        url = f'https://{GITHUB_TOKEN}@github.com/{repo_name}.git'
        subprocess.run(['git', 'clone', url, 'workspace'], check=True)