from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import datetime

# --- User Schemas ---
class UserBase(BaseModel):
    github_id: str
    username: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None

class UserResponse(UserBase):
    id: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True

# --- Repository Schemas ---
class RepositoryBase(BaseModel):
    full_name: str
    default_branch: str = "main"
    is_private: bool = False

class RepositoryResponse(RepositoryBase):
    id: str
    installation_id: Optional[str] = None
    last_scanned_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True

# --- Scan & Finding Schemas ---
class ScanTriggerRequest(BaseModel):
    repository_url: str
    installation_id: Optional[int] = None
    async_execution: bool = Field(default=True, alias="async")

class FindingResponse(BaseModel):
    id: str
    scan_id: str
    title: str
    description: str
    severity: str
    category: str
    confidence: float
    impact: str
    filepath: str
    line_number: int
    code_snippet: Optional[str] = None
    reasoning: Optional[str] = None
    suggested_fix: Optional[str] = None
    created_at: datetime.datetime
    is_fixed: bool = False

    class Config:
        from_attributes = True

class ScanResponse(BaseModel):
    scan_id: str
    repository: str
    status: str
    phase: str
    progress: int
    current_file: Optional[str] = ""
    files_scanned: int = 0
    ignored_files: int = 0
    duration_seconds: float = 0.0
    language_breakdown: Optional[Dict[str, int]] = None
    bugs: List[FindingResponse] = []
    error: Optional[str] = None
    timestamp: str

    class Config:
        from_attributes = True

# --- Fix Schemas ---
class FixRequest(BaseModel):
    repository_url: str
    installation_id: Optional[int] = None
    title: Optional[str] = "Rover bug fix report"
    description: Optional[str] = ""

class FixResponse(BaseModel):
    fix_id: str
    status: str
    issue_number: Optional[int] = None
    pull_request_number: Optional[int] = None
    pull_request_url: Optional[str] = None
    summary: Optional[str] = None

# --- Webhook Schemas ---
class WebhookResponse(BaseModel):
    status: str
    action: Optional[str] = None
    issue: Optional[int] = None
    installation_id: Optional[int] = None
