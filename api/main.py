"""
api/main.py

FastAPI webhook listener for Rover.
GitHub sends a POST to /webhook when an Issue is labeled rover.
We validate the signature, return 200 immediately, and run the
agent in the background so GitHub does not time out.
"""
import hmac, hashlib, json, os
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from dotenv import load_dotenv
from src.agent import run_agent_for_issue

load_dotenv()
app = FastAPI(title='Rover', version='1.0')


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