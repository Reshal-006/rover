import uuid
import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from apps.backend.app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    github_id = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, nullable=False)
    email = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    access_token = Column(String, nullable=True)
    installation_id = Column(Integer, nullable=True)
    account_type = Column(String, default="User")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    user_preferences = Column(JSON, nullable=True, default={})

    fix_runs = relationship("FixRun", back_populates="user")
    repositories = relationship("Repository", back_populates="user", cascade="all, delete-orphan")

class Installation(Base):
    __tablename__ = "installations"

    id = Column(String, primary_key=True, default=generate_uuid)
    github_installation_id = Column(Integer, unique=True, index=True, nullable=False)
    account_name = Column(String, nullable=False)
    account_type = Column(String, default="User")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    repositories = relationship("Repository", back_populates="installation", cascade="all, delete-orphan")

class Repository(Base):
    __tablename__ = "repositories"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), index=True, nullable=True)
    installation_id = Column(String, ForeignKey("installations.id"), nullable=True)
    full_name = Column(String, index=True, nullable=False)
    default_branch = Column(String, default="main")
    is_private = Column(Boolean, default=False)
    language = Column(String, nullable=True)
    size_kb = Column(Integer, default=0)
    open_issues = Column(Integer, default=0)
    pull_requests = Column(Integer, default=0)
    health_score = Column(Integer, default=100)
    ai_readiness_score = Column(Integer, default=100)
    security_grade = Column(String, default="A+")
    last_scanned_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="repositories")
    installation = relationship("Installation", back_populates="repositories")
    scans = relationship("Scan", back_populates="repository", cascade="all, delete-orphan")


class Scan(Base):
    __tablename__ = "scans"

    id = Column(String, primary_key=True, default=generate_uuid)
    repository_id = Column(String, ForeignKey("repositories.id"), nullable=True)
    repository_url = Column(String, nullable=False)
    status = Column(String, default="scanning")  # scanning, completed, failed
    phase = Column(String, default="cloning")
    progress = Column(Integer, default=0)
    current_file = Column(String, nullable=True)
    files_scanned = Column(Integer, default=0)
    ignored_files = Column(Integer, default=0)
    duration_seconds = Column(Float, default=0.0)
    language_breakdown = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    repository = relationship("Repository", back_populates="scans")
    findings = relationship("Finding", back_populates="scan", cascade="all, delete-orphan")

class Finding(Base):
    __tablename__ = "findings"

    id = Column(String, primary_key=True, default=generate_uuid)
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String, default="medium")  # low, medium, high, critical
    category = Column(String, default="Security")
    confidence = Column(Float, default=0.8)
    impact = Column(String, default="medium")
    filepath = Column(String, nullable=False)
    line_number = Column(Integer, default=1)
    code_snippet = Column(Text, nullable=True)
    reasoning = Column(Text, nullable=True)
    suggested_fix = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    scan = relationship("Scan", back_populates="findings")
    fix_runs = relationship("FixRun", back_populates="finding")

class FixRun(Base):
    __tablename__ = "fix_runs"

    id = Column(String, primary_key=True, default=generate_uuid)
    finding_id = Column(String, ForeignKey("findings.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    repo_name = Column(String, nullable=False)
    issue_number = Column(Integer, nullable=True)
    status = Column(String, default="running")  # running, completed, failed
    branch_name = Column(String, nullable=True)
    pull_request_number = Column(Integer, nullable=True)
    pull_request_url = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    duration_seconds = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    finding = relationship("Finding", back_populates="fix_runs")
    user = relationship("User", back_populates="fix_runs")
