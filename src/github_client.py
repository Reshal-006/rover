"""
github_client.py — all GitHub API interactions for Rover.
"""
from github import Github
import os, subprocess
from dotenv import load_dotenv

load_dotenv()
g = Github(os.getenv('GITHUB_TOKEN'))

def get_issue_text(repo_name: str, issue_number: int) -> str:
    repo  = g.get_repo(repo_name)
    issue = repo.get_issue(issue_number)
    return f'Title: {issue.title}\n\n{issue.body or "No description."}'

def post_comment(repo_name: str, issue_number: int, body: str):
    repo  = g.get_repo(repo_name)
    issue = repo.get_issue(issue_number)
    issue.create_comment(body)
    print(f'Comment posted on Issue #{issue_number}')

def clone_repo(repo_name: str):
    if os.path.exists('workspace'):
        subprocess.run(['git', 'pull'], cwd='workspace', check=False)
    else:
        token = os.getenv('GITHUB_TOKEN')
        url   = f'https://{token}@github.com/{repo_name}.git'
        subprocess.run(['git', 'clone', url, 'workspace'], check=True)