import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request, BackgroundTasks, HTTPException
import hmac, hashlib, json
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv()

from apps.backend.app.core.config import settings
from apps.backend.app.core.database import init_db
from apps.backend.app.api.v1.endpoints import router as api_v1_router
from src.agent import run_agent_for_issue

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

@app.on_event("startup")
async def on_startup():
    await init_db()

# Enable CORS for React SPA
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {"message": "Welcome to Rover Enterprise AI API v2.0", "docs": "/docs"}


def _verify_github_signature(payload: bytes, sig_header: str) -> bool:
    secret = settings.WEBHOOK_SECRET or ""
    if not secret or not sig_header:
        return False
    expected = 'sha256=' + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig_header)


@app.post('/webhook')
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.body()
    sig_header = request.headers.get('X-Hub-Signature-256', '')

    if not _verify_github_signature(payload, sig_header):
        raise HTTPException(status_code=403, detail='Invalid signature')

    event_type = request.headers.get('X-GitHub-Event', '')
    if event_type != 'issues':
        return {'status': 'ignored', 'reason': f'not an issue event: {event_type}'}

    data = json.loads(payload)
    action = data.get('action', '')
    installation_id = data.get('installation', {}).get('id')

    if action == 'labeled':
        label_name = data.get('label', {}).get('name', '')
        if label_name == 'rover':
            repo_name = data['repository']['full_name']
            issue_number = data['issue']['number']
            background_tasks.add_task(
                run_agent_for_issue,
                repo_name,
                issue_number,
                installation_id=installation_id
            )
            return {'status': 'agent triggered', 'issue': issue_number, 'installation_id': installation_id}

    return {'status': 'ignored', 'action': action}
