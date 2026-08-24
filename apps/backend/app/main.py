import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request, BackgroundTasks, HTTPException, Response
import hmac, hashlib, json, time
from dotenv import load_dotenv
import logging

try:
    import redis.asyncio as redis
except Exception:
    redis = None

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv()

from apps.backend.app.core.config import settings
from apps.backend.app.core.database import init_db
from apps.backend.app.api.v1.endpoints import router as api_v1_router
from src.agent import run_agent_for_issue
from fastapi.responses import JSONResponse
from src.github_auth import GitHubAPIError, GitHubAppAuthError

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

logger = logging.getLogger("rover.backend")

# lightweight in-memory rate limiter store
app.state._rate_limits = {}
app.state._redis = None

@app.on_event("startup")
async def on_startup():
    await init_db()
    # Initialize Redis client if configured and available
    redis_url = settings.REDIS_URL
    if redis and redis_url:
        try:
            app.state._redis = redis.from_url(redis_url, decode_responses=True)
            # test connection
            await app.state._redis.ping()
            logger.info("Connected to Redis for rate-limiting and caching")
        except Exception as e:
            logger.warning("Unable to connect to Redis (%s): %s", redis_url, e)
            app.state._redis = None

# Enable CORS for React SPA (restrict to configured frontend)
allowed_origins = [settings.FRONTEND_URL.rstrip('/')]
if settings.BACKEND_URL:
    allowed_origins.append(settings.BACKEND_URL.rstrip('/'))

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys(allowed_origins)),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _simple_rate_limiter(request: Request, call_next):
    try:
        ip = request.client.host or "unknown"
    except Exception:
        ip = "unknown"

    # Prefer Redis-backed rate limiting (atomic and shared across instances).
    redis_client = getattr(app.state, "_redis", None)
    window = settings.RATE_LIMIT_WINDOW_SECONDS
    max_requests = settings.RATE_LIMIT_MAX_REQUESTS

    if redis_client is not None:
        key = f"rate:{ip}"
        try:
            count = await redis_client.incr(key)
            if count == 1:
                await redis_client.expire(key, window)
            if count > max_requests:
                return JSONResponse(status_code=429, content={"detail": "Too Many Requests"})
        except Exception as e:
            # Redis failed; fall back to in-memory limiter but log the incident
            logger.warning("Redis rate limiter failure, falling back to memory: %s", e)

    # In-memory fallback (per-process, not global across instances)
    now = time.time()
    bucket = app.state._rate_limits.get(ip)
    if not bucket:
        app.state._rate_limits[ip] = {"count": 1, "start": now}
    else:
        elapsed = now - bucket["start"]
        if elapsed > window:
            bucket["count"] = 1
            bucket["start"] = now
        else:
            bucket["count"] += 1

    if app.state._rate_limits[ip]["count"] > max_requests:
        return JSONResponse(status_code=429, content={"detail": "Too Many Requests"})

    return await call_next(request)

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


@app.exception_handler(GitHubAPIError)
async def _handle_github_api_error(request: Request, exc: GitHubAPIError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(GitHubAppAuthError)
async def _handle_github_auth_error(request: Request, exc: GitHubAppAuthError):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def _handle_unexpected_error(request: Request, exc: Exception):
    # Generic 500 with minimal info — details are logged server-side only
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


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
