"""
api/main.py

FastAPI webhook listener for Rover.
GitHub sends a POST to /webhook when an Issue is labeled rover.
We validate the signature, return 200 immediately, and run the
agent in the background so GitHub does not time out.
"""
import hmac, hashlib, json, os, sys, time, uuid
from pathlib import Path
import logging
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.agent import run_agent_for_issue
from src.scanner import scan_repository, validate_repository_url
from src.storage import ScanStore
from src.github_client import create_issue_from_scan
from src.github_auth import save_installation_id, load_installation_id

load_dotenv()
app = FastAPI(title='Rover', version='1.0')
logger = logging.getLogger("rover.api")
scan_store = ScanStore()


def verify_github_signature(payload: bytes, sig_header: str) -> bool:
    '''
    GitHub signs every webhook with your WEBHOOK_SECRET.
    We recompute the signature and compare with hmac.compare_digest
    to prevent timing attacks.
    '''
    secret = os.getenv('WEBHOOK_SECRET', '')
    expected = 'sha256=' + hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, sig_header)


@app.get('/')
def health_check():
    '''Health check endpoint — confirms the server is running.'''
    return {'status': 'Rover is running', 'version': '1.0'}


@app.get('/github/callback')
async def github_callback(installation_id: int, setup_action: str = None):
    """
    Receives redirect from GitHub App installation.
    Saves the installation ID securely and redirects back to Streamlit dashboard.
    """
    if not installation_id:
        logger.error("GitHub App installation callback failed: installation_id is missing.")
        raise HTTPException(status_code=400, detail="Missing installation_id")

    try:
        save_installation_id(installation_id)
        logger.info("GitHub App installation callback successful. Saved installation_id: %s", installation_id)
    except Exception as e:
        logger.error("Failed to save installation ID %s: %s", installation_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to save installation ID: {e}")

    # Redirect to the Streamlit dashboard
    dashboard_url = os.getenv("DASHBOARD_URL", "http://localhost:8501")
    return RedirectResponse(url=dashboard_url)


@app.post('/scan')
async def trigger_scan(payload: dict, background_tasks: BackgroundTasks):
    repository_url = payload.get('repository_url', '').strip()
    if not validate_repository_url(repository_url):
        raise HTTPException(status_code=400, detail='Invalid GitHub repository URL')

    USE_GITHUB_APP = os.getenv('USE_GITHUB_APP', 'false').lower() == 'true'
    if USE_GITHUB_APP:
        repo_name = repository_url.replace('https://github.com/', '').rstrip('/')
        installation_id = load_installation_id()
        if not installation_id:
            raise HTTPException(status_code=400, detail="USE_GITHUB_APP is true but no GitHub App installation ID is stored.")
        from src.github_auth import check_repository_access
        if not check_repository_access(installation_id, repo_name):
            raise HTTPException(status_code=403, detail=f"Access Denied: GitHub App does not have access to repository '{repo_name}' or is not installed.")

    scan_id = f"scan-{uuid.uuid4().hex[:8]}"
    result = {
        'scan_id': scan_id,
        'repository': repository_url,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'bugs': [],
        'status': 'scanning',
        'severity': {},
    }
    scan_store.save_scan(result)

    if payload.get('async', False):
        def _run_scan() -> None:
            try:
                scan_repository(repository_url, scan_id=scan_id)
            except Exception as exc:  # pragma: no cover - defensive path
                failed = {
                    'scan_id': scan_id,
                    'repository': repository_url,
                    'status': 'failed',
                    'error': str(exc),
                    'bugs': [],
                    'phase': 'failed',
                    'progress': 100
                }
                scan_store.save_scan(failed)

        background_tasks.add_task(_run_scan)
        return result

    try:
        scan_result = scan_repository(repository_url, scan_id=scan_id)
        return scan_result
    except Exception as exc:  # pragma: no cover - defensive path
        failed = {
            'scan_id': scan_id,
            'repository': repository_url,
            'status': 'failed',
            'error': str(exc),
            'bugs': [],
            'phase': 'failed',
            'progress': 100
        }
        scan_store.save_scan(failed)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get('/scan/{scan_id}')
async def get_scan(scan_id: str):
    return scan_store.load_scan(scan_id)


@app.get('/bugs/{scan_id}')
async def get_bugs(scan_id: str):
    scan = scan_store.load_scan(scan_id)
    return scan.get('bugs', [])


@app.post('/fix/{bug_id}')
async def fix_bug(bug_id: str, payload: dict, background_tasks: BackgroundTasks):
    repository_url = payload.get('repository_url', '').strip()
    if not validate_repository_url(repository_url):
        raise HTTPException(status_code=400, detail='Invalid GitHub repository URL')

    issue_number = create_issue_from_scan(repository_url, bug_id, payload.get('title', 'Rover bug report'), payload.get('description', ''))
    background_tasks.add_task(run_agent_for_issue, repository_url.replace('https://github.com/', ''), int(issue_number))
    return {'status': 'issue-created', 'issue_number': issue_number}


@app.post('/webhook')
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    '''
    Receives GitHub webhook events.
    Returns 200 immediately and runs the agent in the background.
    '''
    payload    = await request.body()
    sig_header = request.headers.get('X-Hub-Signature-256', '')

    # Reject requests that did not come from GitHub
    if not verify_github_signature(payload, sig_header):
        raise HTTPException(status_code=403, detail='Invalid signature')

    event_type = request.headers.get('X-GitHub-Event', '')

    # We only care about Issue events
    if event_type != 'issues':
        return {'status': 'ignored', 'reason': f'not an issue event: {event_type}'}

    data   = json.loads(payload)
    action = data.get('action', '')

    # Only trigger when the rover label is added to an Issue
    if action == 'labeled':
        label_name = data.get('label', {}).get('name', '')
        if label_name == 'rover':
            repo_name    = data['repository']['full_name']
            issue_number = data['issue']['number']
            # Return 200 to GitHub first — agent runs in background
            # GitHub times out if we do not respond within 10 seconds
            background_tasks.add_task(
                run_agent_for_issue,
                repo_name,
                issue_number
            )
            return {'status': 'agent triggered', 'issue': issue_number}

    return {'status': 'ignored', 'action': action}