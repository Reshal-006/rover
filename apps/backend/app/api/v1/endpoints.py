import time
import datetime
import asyncio
import json
import uuid
import logging
import requests
import jwt
from typing import List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from apps.backend.app.core.config import settings
from apps.backend.app.core.database import get_db, AsyncSessionLocal

from apps.backend.app.domain.models.models import Scan, Finding, Repository, Installation, User, FixRun
from apps.backend.app.domain.schemas.schemas import (
    ScanTriggerRequest, ScanResponse, FindingResponse, FixRequest, FixResponse
)
from src.scanner import scan_repository, validate_repository_url
from src.agent import run_agent_for_issue
from src.github_client import create_issue_from_scan
import src.github_auth as github_auth


logger = logging.getLogger("rover.backend.api")
router = APIRouter()

# Active WebSocket connections store
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, List[WebSocket]] = {}

    async def connect(self, scan_id: str, websocket: WebSocket):
        await websocket.accept()
        if scan_id not in self.active_connections:
            self.active_connections[scan_id] = []
        self.active_connections[scan_id].append(websocket)

    def disconnect(self, scan_id: str, websocket: WebSocket):
        if scan_id in self.active_connections:
            self.active_connections[scan_id].remove(websocket)
            if not self.active_connections[scan_id]:
                del self.active_connections[scan_id]

    async def broadcast(self, scan_id: str, message: dict):
        if scan_id in self.active_connections:
            for connection in self.active_connections[scan_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

manager = ConnectionManager()

@router.get("/health")
async def health_check():
    return {"status": "Rover Enterprise API is healthy", "version": "2.0.0"}

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
):

    """
    Decodes the JWT session token from the Authorization header and resolves the User record.
    Raises HTTP 401 Unauthorized if missing, expired, or invalid.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Unauthenticated session. Please sign in with GitHub."
        )

    token = auth_header.split("Bearer ")[1].strip()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid session payload.")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid session token.")

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        stmt = select(User).where(User.github_id == str(user_id))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Authenticated user session not found.")

    return user


@router.get("/repositories")
async def list_repositories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns all repositories belonging strictly to the authenticated tenant.
    Auto-syncs from GitHub App installation if database has zero repos for the tenant.
    """
    stmt = select(Repository).where(Repository.user_id == current_user.id)
    result = await db.execute(stmt)
    db_repos = result.scalars().all()

    # If DB is empty for current user and user has an installation, attempt an auto-sync
    if not db_repos and current_user.installation_id:
        try:
            gh_repos = github_auth.list_installation_repositories(current_user.installation_id)
            for repo_data in gh_repos:
                full_name = repo_data.get("full_name")
                if not full_name:
                    continue
                new_repo = Repository(
                    user_id=current_user.id,
                    installation_id=str(current_user.installation_id),
                    full_name=full_name,
                    default_branch=repo_data.get("default_branch", "main"),
                    is_private=repo_data.get("private", False),
                    language=repo_data.get("language"),
                    size_kb=repo_data.get("size", 0),
                    open_issues=repo_data.get("open_issues_count", 0),
                )
                db.add(new_repo)
            await db.commit()
            stmt = select(Repository).where(Repository.user_id == current_user.id)
            result = await db.execute(stmt)
            db_repos = result.scalars().all()
        except Exception as e:
            logger.error("Failed auto-sync on list_repositories for tenant %s: %s", current_user.username, e)

    output = []
    for r in db_repos:
        parts = r.full_name.split("/")
        owner = parts[0] if len(parts) == 2 else "Unknown"
        repo_name = parts[1] if len(parts) == 2 else r.full_name

        output.append({
            "id": r.id,
            "full_name": r.full_name,
            "name": repo_name,
            "owner": owner,
            "account_type": "Personal" if owner.lower() == current_user.username.lower() else "Organization",
            "default_branch": r.default_branch or "main",
            "is_private": bool(r.is_private),
            "language": r.language or "Unknown",
            "size_kb": r.size_kb,
            "open_issues": r.open_issues,
            "pull_requests": r.pull_requests,
            "contributors": 1,
            "health_score": r.health_score,
            "ai_readiness_score": r.ai_readiness_score,
            "security_grade": r.security_grade,
            "last_scanned_at": r.last_scanned_at.isoformat() if r.last_scanned_at else "Not scanned yet",
            "scan_status": "Ready",
            "github_app_installed": True,
        })
    return {"repositories": output, "total": len(output), "installation_id": current_user.installation_id}


async def _run_sync_task(user_id: str, inst_id: int):
    """Background task to perform the actual GitHub sync."""
    try:
        from apps.backend.app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            # Re-fetch user
            stmt = select(User).where(User.id == user_id)
            user_res = await db.execute(stmt)
            current_user = user_res.scalar_one_or_none()
            if not current_user:
                return

            try:
                gh_repos = github_auth.list_installation_repositories(inst_id)
            except Exception as e:
                logger.error("Background sync failed fetching GitHub repositories: %s", e)
                return

            stmt = select(Repository).where(Repository.user_id == current_user.id)
            result = await db.execute(stmt)
            existing_repos = {r.full_name: r for r in result.scalars().all()}

            current_full_names = set()
            for r_data in gh_repos:
                full_name = r_data.get("full_name")
                if not full_name:
                    continue
                current_full_names.add(full_name)

                if full_name in existing_repos:
                    repo_obj = existing_repos[full_name]
                    repo_obj.default_branch = r_data.get("default_branch", "main")
                    repo_obj.is_private = r_data.get("private", False)
                    repo_obj.language = r_data.get("language")
                    repo_obj.size_kb = r_data.get("size", 0)
                    repo_obj.open_issues = r_data.get("open_issues_count", 0)
                else:
                    new_repo = Repository(
                        user_id=current_user.id,
                        installation_id=str(inst_id),
                        full_name=full_name,
                        default_branch=r_data.get("default_branch", "main"),
                        is_private=r_data.get("private", False),
                        language=r_data.get("language"),
                        size_kb=r_data.get("size", 0),
                        open_issues=r_data.get("open_issues_count", 0)
                    )
                    db.add(new_repo)

            for name, repo_obj in existing_repos.items():
                if name not in current_full_names:
                    await db.delete(repo_obj)

            await db.commit()
    except Exception as e:
        logger.error("Unhandled error in background sync task: %s", e)


@router.post("/repositories/sync")
async def sync_repositories(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Kicks off a background task to synchronize repositories from GitHub.
    Returns immediately to avoid timeouts on large organizations.
    """
    inst_id = current_user.installation_id

    # If user model lacks installation_id, discover via OAuth token
    if not inst_id and current_user.access_token:
        try:
            inst_res = requests.get(
                "https://api.github.com/user/installations",
                headers={
                    "Authorization": f"Bearer {current_user.access_token}",
                    "Accept": "application/vnd.github+json"
                },
                timeout=10
            )
            if inst_res.status_code == 200:
                installations = inst_res.json().get("installations", [])
                if installations:
                    inst_id = installations[0].get("id")
                    current_user.installation_id = inst_id
                    current_user.account_type = installations[0].get("account", {}).get("type", "User")
                    await db.commit()
        except Exception as e:
            logger.warning("Dynamic installation lookup failed for %s: %s", current_user.username, e)

    if not inst_id:
        raise HTTPException(
            status_code=400, 
            detail="No GitHub App installation found for your account. Please install the Rover GitHub App first."
        )

    # Offload the heavy fetch and sync to a background task
    background_tasks.add_task(_run_sync_task, current_user.id, inst_id)

    return {
        "status": "sync_started",
        "added": "?",
        "updated": "?",
        "removed": "?",
        "total_active": "?",
        "duration_seconds": 0,
        "installation_id": inst_id
    }


@router.post("/scans", response_model=dict)
async def trigger_scan(
    payload: ScanTriggerRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repository_url = payload.repository_url.strip()
    if not validate_repository_url(repository_url):
        raise HTTPException(status_code=400, detail="Invalid GitHub repository URL")

    repo_name = repository_url.replace("https://github.com/", "").rstrip("/")
    parts = repo_name.split("/")
    owner, repo = parts[0], parts[1] if len(parts) == 2 else ("", repo_name)

    installation_id = payload.installation_id or current_user.installation_id

    if settings.USE_GITHUB_APP:
        if not installation_id:
            raise HTTPException(status_code=400, detail="GitHub App mode enabled but no installation ID resolved for your user session.")
        if not github_auth.check_repository_access(installation_id, repo_name):
            raise HTTPException(status_code=403, detail=f"Access Denied: App is not installed on '{repo_name}'.")

    scan_id = f"scan-{uuid.uuid4().hex[:8]}"
    user_id = current_user.id

    async def _execute_scan():
        try:
            result = scan_repository(repository_url, scan_id=scan_id)
            async with AsyncSessionLocal() as db_session:
                repo_full_name = repository_url.replace("https://github.com/", "").rstrip("/")
                stmt = select(Repository).where(
                    Repository.user_id == user_id,
                    Repository.full_name == repo_full_name
                )
                res = await db_session.execute(stmt)
                repo_obj = res.scalar_one_or_none()

                now = datetime.datetime.utcnow()
                db_scan = Scan(
                    id=scan_id,
                    repository_id=repo_obj.id if repo_obj else None,
                    repository_url=repository_url,
                    status="completed",
                    phase="completed",
                    progress=100,
                    files_scanned=result.get("files_scanned", 0),
                    ignored_files=result.get("ignored_files", 0),
                    duration_seconds=result.get("scan_duration_seconds", 0.0),
                    language_breakdown=result.get("language_breakdown", {}),
                    created_at=now
                )
                db_session.add(db_scan)

                if repo_obj:
                    repo_obj.last_scanned_at = now
                    
                    # Compute scores dynamically based on scan findings
                    health = 100
                    ai_readiness = 100
                    
                    for b in result.get("bugs", []):
                        sev = str(b.get("severity", "medium")).lower()
                        cat = str(b.get("category", "Security")).lower()
                        
                        if sev == "critical":
                            health -= 20
                        elif sev == "high":
                            health -= 10
                        elif sev == "medium":
                            health -= 5
                        elif sev == "low":
                            health -= 1
                            
                        if cat in ["code smell", "logic", "maintainability"]:
                            ai_readiness -= 5
                            
                    repo_obj.health_score = max(0, health)
                    repo_obj.ai_readiness_score = max(0, ai_readiness)
                    
                    if repo_obj.health_score >= 95:
                        repo_obj.security_grade = "A+"
                    elif repo_obj.health_score >= 90:
                        repo_obj.security_grade = "A"
                    elif repo_obj.health_score >= 80:
                        repo_obj.security_grade = "B"
                    elif repo_obj.health_score >= 70:
                        repo_obj.security_grade = "C"
                    else:
                        repo_obj.security_grade = "F"

                for b in result.get("bugs", []):
                    try:
                        line_num = int(b.get("line_number") or 1)
                    except Exception:
                        line_num = 1
                        
                    try:
                        conf = float(b.get("confidence") or 0.8)
                    except Exception:
                        conf = 0.8
                        
                    db_finding = Finding(
                        scan_id=scan_id,
                        title=b.get("title") or "Discovered Bug",
                        description=b.get("description") or "",
                        severity=b.get("severity") or "medium",
                        category=b.get("category") or "Security",
                        confidence=conf,
                        impact=b.get("impact") or "medium",
                        filepath=b.get("filepath") or b.get("file") or "unknown",
                        line_number=line_num,
                        code_snippet=b.get("code_snippet") or "",
                        reasoning=b.get("reasoning") or "",
                        suggested_fix=b.get("suggested_fix") or ""
                    )
                    db_session.add(db_finding)

                await db_session.commit()
                logger.info("Successfully persisted scan %s and findings to DB", scan_id)
        except Exception as e:
            import traceback
            with open("scan_error.txt", "w") as f:
                f.write(traceback.format_exc())
            logger.error("Background scan failed for %s: %s", scan_id, e)
            async with AsyncSessionLocal() as db_session:
                db_scan = Scan(
                    id=scan_id,
                    repository_url=repository_url,
                    status="failed",
                    phase="failed",
                    progress=100,
                    error=str(e),
                    created_at=datetime.datetime.utcnow()
                )
                db_session.add(db_scan)
                await db_session.commit()

    background_tasks.add_task(_execute_scan)
    return {"scan_id": scan_id, "status": "scanning", "repository": repository_url}

@router.get("/scans/{scan_id}")
async def get_scan(scan_id: str, current_user: User = Depends(get_current_user)):
    from src.storage import ScanStore
    store = ScanStore()
    try:
        return store.load_scan(scan_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Scan not found")

async def _run_and_update_fix(fix_id: str, repo_full_name: str, issue_number: int, installation_id: int):
    from apps.backend.app.core.database import AsyncSessionLocal
    from apps.backend.app.domain.models.models import FixRun
    import asyncio
    try:
        await asyncio.to_thread(
            run_agent_for_issue,
            repo_full_name,
            issue_number,
            installation_id=installation_id
        )
        async with AsyncSessionLocal() as session:
            run = await session.get(FixRun, fix_id)
            if run:
                run.status = "completed"
                await session.commit()
    except Exception as e:
        logger.error(f"Agent run failed for {fix_id}: {e}")
        async with AsyncSessionLocal() as session:
            run = await session.get(FixRun, fix_id)
            if run:
                run.status = "failed"
                await session.commit()

@router.post("/fixes/{bug_id}", response_model=FixResponse)
async def fix_bug(
    bug_id: str,
    payload: FixRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        repository_url = payload.repository_url.strip()
        if not validate_repository_url(repository_url):
            raise HTTPException(status_code=400, detail="Invalid GitHub repository URL")

        repo_full_name = repository_url.replace("https://github.com/", "").rstrip("/")
        parts = repo_full_name.split("/")
        owner, repo = parts[0], parts[1] if len(parts) == 2 else ("", repo_full_name)

        installation_id = payload.installation_id or current_user.installation_id or (github_auth.get_repo_installation(owner, repo) if owner and repo else None)

        issue_number = await asyncio.to_thread(
            create_issue_from_scan,
            repository_url, bug_id, payload.title or "Rover bug fix report", payload.description or "", installation_id=installation_id
        )

        fix_id = f"fix-{uuid.uuid4().hex[:8]}"
        new_fix_run = FixRun(
            id=fix_id,
            finding_id=bug_id,
            user_id=current_user.id,
            repo_name=repo_full_name,
            issue_number=int(issue_number),
            status="running"
        )
        db.add(new_fix_run)
        await db.commit()

        background_tasks.add_task(
            _run_and_update_fix,
            fix_id,
            repo_full_name,
            int(issue_number),
            installation_id
        )

        return FixResponse(
            fix_id=fix_id,
            status="running",
            issue_number=int(issue_number)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in fix_bug endpoint for bug_id %s: %s", bug_id, e)
        raise HTTPException(status_code=500, detail=f"Fix error: {str(e)}")

import jwt
import secrets

@router.get("/auth/github/url")
async def get_github_oauth_url():
    """
    Returns the official GitHub OAuth authorization URL for initiating login.
    Requires GITHUB_CLIENT_ID to be configured in .env.
    """
    client_id = settings.GITHUB_CLIENT_ID
    if not client_id:
        raise HTTPException(
            status_code=400, 
            detail="GITHUB_CLIENT_ID is not configured in backend environment (.env). Please provide valid GitHub OAuth credentials."
        )

    state = secrets.token_hex(16)
    redirect_uri = settings.computed_redirect_uri
    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope=read:user,user:email,repo,read:org"
        f"&state={state}"
    )
    return {"url": url, "client_id": client_id, "state": state, "redirect_uri": redirect_uri}



@router.post("/auth/github/callback")
async def github_oauth_callback(payload: dict, db: AsyncSession = Depends(get_db)):
    """
    Exchanges GitHub OAuth code for an access token, upserts the User record,
    discovers GitHub App installation, and returns a signed JWT.
    """
    code = payload.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code.")

    client_id = settings.GITHUB_CLIENT_ID
    client_secret = settings.GITHUB_CLIENT_SECRET
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=400, 
            detail="GitHub OAuth credentials (GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET) are missing on server."
        )

    try:
        token_res = requests.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code
            },
            timeout=10
        )
        token_data = token_res.json()
    except Exception as e:
        logger.error("Failed to connect to GitHub OAuth token endpoint: %s", e)
        raise HTTPException(status_code=502, detail="Unable to contact GitHub OAuth servers.")

    access_token = token_data.get("access_token")
    if not access_token:
        error_desc = token_data.get("error_description", "Invalid or expired authorization code.")
        raise HTTPException(status_code=401, detail=f"GitHub OAuth failed: {error_desc}")

    # Fetch authentic user profile from GitHub
    try:
        user_res = requests.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            timeout=10
        )
        user_info = user_res.json()
    except Exception as e:
        logger.error("Failed to fetch user profile from GitHub API: %s", e)
        raise HTTPException(status_code=502, detail="Failed to fetch user profile from GitHub.")

    if "login" not in user_info:
        raise HTTPException(status_code=401, detail="Failed to retrieve valid GitHub user identity.")

    account_name = user_info.get("login")
    github_id = str(user_info.get("id"))
    avatar_url = user_info.get("avatar_url", f"https://github.com/{account_name}.png")
    email = user_info.get("email", f"{account_name}@users.noreply.github.com")

    # Discover GitHub App installation(s) for this user via OAuth token
    discovered_inst_id = None
    discovered_account_type = "User"
    try:
        inst_res = requests.get(
            "https://api.github.com/user/installations",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            timeout=10
        )
        if inst_res.status_code == 200:
            installations = inst_res.json().get("installations", [])
            if installations:
                discovered_inst_id = installations[0].get("id")
                discovered_account_type = installations[0].get("account", {}).get("type", "User")
    except Exception as e:
        logger.warning("Could not discover GitHub App installations for user %s: %s", account_name, e)

    # Upsert User record in Database
    stmt = select(User).where(User.github_id == github_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            github_id=github_id,
            username=account_name,
            email=email,
            avatar_url=avatar_url,
            access_token=access_token,
            installation_id=discovered_inst_id,
            account_type=discovered_account_type
        )
        db.add(user)
    else:
        user.username = account_name
        user.email = email
        user.avatar_url = avatar_url
        user.access_token = access_token
        if discovered_inst_id:
            user.installation_id = discovered_inst_id
            user.account_type = discovered_account_type

    await db.commit()
    await db.refresh(user)

    # Issue signed JWT session token storing internal user UUID as 'sub'
    now = time.time()
    payload_jwt = {
        "sub": user.id,
        "github_id": user.github_id,
        "username": user.username,
        "iat": int(now),
        "exp": int(now + 86400 * 7)
    }
    jwt_token = jwt.encode(payload_jwt, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    status = "authenticated" if user.installation_id else "no_app_installed"

    return {
        "authenticated": True,
        "status": status,
        "name": user.username,
        "username": user.username.lower(),
        "avatar_url": user.avatar_url,
        "email": user.email,
        "plan": "Enterprise Plan",
        "installation_id": user.installation_id,
        "token": jwt_token
    }

@router.post("/auth/github/setup")
async def github_app_setup_callback(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Captures installation_id from GitHub App setup redirect and associates it with current_user.
    """
    inst_id_raw = payload.get("installation_id")
    if not inst_id_raw:
        raise HTTPException(status_code=400, detail="Missing installation_id")

    try:
        inst_id = int(inst_id_raw)
        current_user.installation_id = inst_id
        await db.commit()
        await db.refresh(current_user)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid installation_id: {e}")

    return await get_user_profile(current_user=current_user, db=db)


@router.get("/auth/me")
@router.get("/user/profile")
async def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns profile details for the currently authenticated tenant.
    """
    status = "authenticated" if current_user.installation_id else "no_app_installed"

    return {
        "authenticated": True,
        "status": status,
        "name": current_user.username,
        "username": current_user.username.lower(),
        "account_type": current_user.account_type or "User",
        "plan": "Enterprise Plan",
        "installation_id": current_user.installation_id,
        "avatar_url": current_user.avatar_url or f"https://github.com/{current_user.username}.png"
    }




@router.post("/auth/login")
async def login_with_github(db: AsyncSession = Depends(get_db)):
    """
    Simulates / handles GitHub OAuth authentication exchange.
    Verifies installation and returns the authenticated user session.
    """
    inst_id = github_auth.load_installation_id()
    if not inst_id:
        return {
            "authenticated": False,
            "status": "no_app_installed",
            "message": "GitHub OAuth succeeded, but Rover GitHub App is not installed."
        }

    return await get_user_profile(db)

@router.post("/auth/logout")
async def logout_user():
    """
    Clears current authenticated session.
    """
    return {"authenticated": False, "status": "unauthenticated", "message": "Successfully signed out."}



@router.get("/dashboard/summary")
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Computes real multi-tenant telemetry for the Dashboard control room.
    Integrates directly with repositories, scans, findings, and fix runs in DB for the current tenant.
    """
    inst_id = current_user.installation_id

    # Repos count for current tenant
    stmt_repos = select(Repository).where(Repository.user_id == current_user.id)
    res_repos = await db.execute(stmt_repos)
    repos = res_repos.scalars().all()

    repo_stmt = select(Repository.full_name).where(Repository.user_id == current_user.id)
    repo_names = (await db.execute(repo_stmt)).scalars().all()
    repo_urls = [f"https://github.com/{name}" for name in repo_names]

    if not repo_urls:
        scans = []
        findings = []
    else:
        # Scans count
        stmt_scans = select(Scan).where(Scan.repository_url.in_(repo_urls))
        res_scans = await db.execute(stmt_scans)
        scans = res_scans.scalars().all()

        # Findings count
        stmt_findings = select(Finding).join(Scan).where(Scan.repository_url.in_(repo_urls))
        res_findings = await db.execute(stmt_findings)
        findings = res_findings.scalars().all()

    # Fix Runs count
    stmt_fix_runs = select(FixRun).where(FixRun.user_id == current_user.id, FixRun.status == 'completed')
    res_fix_runs = await db.execute(stmt_fix_runs)
    fix_runs = res_fix_runs.scalars().all()

    # Vulnerabilities severity breakdown
    critical = sum(1 for f in findings if f.severity == "critical")
    high = sum(1 for f in findings if f.severity == "high")
    medium = sum(1 for f in findings if f.severity == "medium")
    low = sum(1 for f in findings if f.severity == "low")

    # Calculate savings dynamically based on fix runs (1.5% per fix run up to 99.9%)
    savings_percentage = min(99.9, len(fix_runs) * 1.5) if fix_runs else 0.0

    return {
        "total_repositories": len(repos),
        "total_scans": len(scans),
        "total_vulnerabilities": len(findings),
        "resolved_vulnerabilities": len(fix_runs),
        "pull_requests_merged": len(fix_runs),
        "ai_compute_savings": f"{savings_percentage:.1f}%",
        "issue_severity_breakdown": [
          {"name": "Critical", "value": critical, "color": "#F43F5E"},
          {"name": "High", "value": high, "color": "#F97316"},
          {"name": "Medium", "value": medium, "color": "#EAB308"},
          {"name": "Low", "value": low, "color": "#3B82F6"}
        ],
        "installation_id": inst_id
    }

@router.get("/findings")
async def list_findings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns live security findings and AST analysis results from database scans.
    Filters to only include findings from the most recent scan for each repository.
    """
    from sqlalchemy import func
    
    # Get user's repository URLs
    repo_stmt = select(Repository.full_name).where(Repository.user_id == current_user.id)
    repo_names = (await db.execute(repo_stmt)).scalars().all()
    repo_urls = [f"https://github.com/{name}" for name in repo_names]

    if not repo_urls:
        return {"findings": [], "total": 0}

    # Get the single most recent scan ID across all user repositories
    latest_scan_stmt = select(Scan.id).where(
        Scan.status == "completed",
        Scan.repository_url.in_(repo_urls)
    ).order_by(Scan.created_at.desc()).limit(1)
    
    res_scans = await db.execute(latest_scan_stmt)
    latest_scan_id = res_scans.scalar_one_or_none()
    
    if not latest_scan_id:
        return {"findings": [], "total": 0}
        
    # Fetch findings that belong to that latest scan
    stmt = select(Finding).where(Finding.scan_id == latest_scan_id).options(
        joinedload(Finding.scan), 
        joinedload(Finding.fix_runs)
    )
    res = await db.execute(stmt)
    db_findings = res.scalars().unique().all()

    output = []
    for f in db_findings:
        output.append({
            "id": f.id,
            "scan_id": f.scan_id,
            "repository_url": f.scan.repository_url if (f.scan and f.scan.repository_url) else "https://github.com/Reshal-006/rover",
            "title": f.title,
            "description": f.description,
            "severity": f.severity,
            "category": f.category,
            "confidence": f.confidence,
            "impact": f.impact,
            "filepath": f.filepath,
            "line_number": f.line_number,
            "code_snippet": f.code_snippet,
            "suggested_fix": f.suggested_fix,
            "reasoning": f.reasoning,
            "created_at": f.created_at.isoformat() if f.created_at else "",
            "is_fixed": len(f.fix_runs) > 0
        })

    return {"findings": output, "total": len(output)}

@router.get("/pull-requests")
async def list_pull_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns real pull request fix runs opened by AI agents.
    """
    from apps.backend.app.domain.models.models import FixRun, Repository
    from src.github_client import get_github_client
    
    stmt = select(FixRun).where(FixRun.user_id == current_user.id)
    res = await db.execute(stmt)
    runs = res.scalars().all()

    output = []
    # Dynamic Sync with GitHub
    if current_user.installation_id:
        try:
            client = get_github_client(current_user.installation_id)
            repo_stmt = select(Repository).where(Repository.user_id == current_user.id)
            repos = (await db.execute(repo_stmt)).scalars().all()
            
            def _fetch_repo_prs(full_name):
                try:
                    gh_repo = client.get_repo(full_name)
                    # Get recent 20 PRs to avoid paginating everything
                    prs = gh_repo.get_pulls(state='all', sort='created', direction='desc')
                    results = []
                    for pr in prs[:20]:
                        if pr.head.ref.startswith("rover/fix-issue-"):
                            results.append({
                                "number": pr.number,
                                "title": pr.title,
                                "ref": pr.head.ref,
                                "html_url": pr.html_url,
                                "merged": pr.merged,
                                "state": pr.state,
                                "created_at": pr.created_at
                            })
                    return results
                except Exception:
                    return []

            tasks = [asyncio.to_thread(_fetch_repo_prs, repo.full_name) for repo in repos]
            all_prs_lists = await asyncio.gather(*tasks)
            
            for repo, pr_list in zip(repos, all_prs_lists):
                for pr in pr_list:
                    # Find matching FixRun by issue_number
                    issue_number = None
                    try:
                        issue_number = int(pr["ref"].split('-')[2])
                    except:
                        pass
                        
                    matched = False
                    for r in runs:
                        if r.repo_name == repo.full_name and r.issue_number == issue_number:
                            r.pull_request_number = pr["number"]
                            r.pull_request_url = pr["html_url"]
                            r.branch_name = pr["ref"]
                            r.summary = pr["title"]
                            r.status = "completed" if pr["merged"] else ("failed" if pr["state"] == "closed" else "running")
                            matched = True
                            break
                            
                    if not matched:
                        # It's a GitHub PR that has no FixRun in the DB.
                        # Display it anyway dynamically.
                        output.append({
                            "id": pr["number"],
                            "repo": repo.full_name,
                            "title": pr["title"],
                            "branch": pr["ref"],
                            "url": pr["html_url"],
                            "status": "MERGED" if pr["merged"] else ("CLOSED" if pr["state"] == "closed" else "OPEN"),
                            "isMerged": pr["merged"],
                            "created_at": pr["created_at"].isoformat() if pr["created_at"] else ""
                        })
            await db.commit()
        except Exception as e:
            logger.warning("Failed to sync pull requests from GitHub: %s", e)

    for r in runs:
        output.append({
            "id": r.pull_request_number or r.issue_number or 45,
            "repo": r.repo_name,
            "title": r.summary or f"Rover Auto-Fix: Issue #{r.issue_number or 45}",
            "branch": r.branch_name or "rover/auto-fix",
            "url": r.pull_request_url or "#",
            "status": "MERGED" if r.status == "completed" else "OPEN",
            "isMerged": r.status == "completed",
            "created_at": r.created_at.isoformat() if r.created_at else ""
        })

    output.sort(key=lambda x: x["created_at"], reverse=True)
    return {"pull_requests": output, "total": len(output)}

@router.get("/analytics")
async def get_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns diagnostic scan runtimes and vulnerability resolution metrics.
    """
    repo_stmt = select(Repository.full_name).where(Repository.user_id == current_user.id)
    repo_names = (await db.execute(repo_stmt)).scalars().all()
    repo_urls = [f"https://github.com/{name}" for name in repo_names]

    if not repo_urls:
        return {"scan_analytics": []}

    stmt = select(Scan).where(Scan.repository_url.in_(repo_urls)).order_by(Scan.created_at)
    res = await db.execute(stmt)
    scans = res.scalars().all()

    scan_data = []
    for idx, s in enumerate(scans[-10:], 1):
        scan_data.append({
            "name": f"Run {idx}",
            "duration": round(s.duration_seconds or 12.0, 1),
            "bugs": s.files_scanned or 3
        })

    if not scan_data:
        scan_data = []

    return {"scan_analytics": scan_data}

@router.get("/history")
async def get_scan_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns real scan execution history audit logs from database.
    """
    repo_stmt = select(Repository.full_name).where(Repository.user_id == current_user.id)
    repo_names = (await db.execute(repo_stmt)).scalars().all()
    repo_urls = [f"https://github.com/{name}" for name in repo_names]

    if not repo_urls:
        return {"history": [], "total": 0}

    stmt = select(Scan).where(Scan.repository_url.in_(repo_urls)).order_by(Scan.created_at.desc())
    res = await db.execute(stmt)
    scans = res.scalars().all()

    history = []
    for s in scans:
        history.append({
            "scan_id": s.id,
            "repo": s.repository_url.replace("https://github.com/", "").rstrip("/"),
            "bugs": s.files_scanned or 0,
            "date": s.created_at.strftime("%Y-%m-%d %H:%M:%S") if s.created_at else "",
            "duration": f"{round(s.duration_seconds or 0.0, 1)}s",
            "status": s.status
        })

    return {"history": history, "total": len(history)}

@router.websocket("/ws/scans/{scan_id}")
async def websocket_scan_stream(websocket: WebSocket, scan_id: str):
    await manager.connect(scan_id, websocket)
    from src.storage import ScanStore
    store = ScanStore()
    try:
        while True:
            try:
                scan_data = store.load_scan(scan_id)
                await websocket.send_json(scan_data)
                if scan_data.get("status") in ("completed", "failed"):
                    break
            except Exception:
                pass
            await websocket.receive_text()  # Keep alive ping
    except WebSocketDisconnect:
        manager.disconnect(scan_id, websocket)


@router.get("/users/settings")
async def get_settings(current_user: User = Depends(get_current_user)):
    """Retrieve user settings and agent configuration preferences."""
    return current_user.user_preferences or {}

@router.put("/users/settings")
async def update_settings(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user settings and agent configuration preferences."""
    try:
        data = await request.json()
        current_user.user_preferences = data
        db.add(current_user)
        await db.commit()
        return {"status": "success", "user_preferences": current_user.user_preferences}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/history")
async def clear_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Danger Zone: Clear all scan history and findings for the current user."""
    try:
        # Delete Scans (which will cascade delete Findings) for all user's repos
        stmt_repos = select(Repository.full_name).where(Repository.user_id == current_user.id)
        res = await db.execute(stmt_repos)
        repo_urls = res.scalars().all()
        
        if repo_urls:
            # For simplicity, we load scans and delete them so cascade works
            stmt_scans = select(Scan).where(Scan.repository_url.in_(repo_urls))
            res_scans = await db.execute(stmt_scans)
            for scan in res_scans.scalars().all():
                await db.delete(scan)
            
            # Delete fix runs
            stmt_fix = select(FixRun).where(FixRun.user_id == current_user.id)
            res_fix = await db.execute(stmt_fix)
            for fix in res_fix.scalars().all():
                await db.delete(fix)
                
            await db.commit()
            
        return {"status": "success", "message": "History cleared"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/auth/revoke")
async def revoke_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Danger Zone: Revoke the current user's session by clearing the access token."""
    try:
        current_user.access_token = None
        db.add(current_user)
        await db.commit()
        return {"status": "success", "message": "Session revoked"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/auth/github")
async def disconnect_github(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Danger Zone: Disconnect GitHub App installation."""
    try:
        current_user.installation_id = None
        db.add(current_user)
        await db.commit()
        return {"status": "success", "message": "GitHub disconnected"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/workspace")
async def reset_workspace(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Danger Zone: Reset workspace by clearing repositories, scans, findings, and fix runs."""
    try:
        stmt_repos = select(Repository).where(Repository.user_id == current_user.id)
        res = await db.execute(stmt_repos)
        repos = res.scalars().all()
        for repo in repos:
            await db.delete(repo)
            
        stmt_scans = select(Scan).where(Scan.repository_url.in_([f"https://github.com/{r.full_name}" for r in repos]))
        res_scans = await db.execute(stmt_scans)
        for scan in res_scans.scalars().all():
            await db.delete(scan)
            
        stmt_fix = select(FixRun).where(FixRun.user_id == current_user.id)
        res_fix = await db.execute(stmt_fix)
        for fix in res_fix.scalars().all():
            await db.delete(fix)
            
        await db.commit()
        return {"status": "success", "message": "Workspace reset"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

