from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class BugFinding:
    file: str
    line_number: int
    severity: str
    bug_type: str
    title: str
    description: str
    confidence: float
    estimated_impact: str = "Medium impact"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["confidence"] = round(float(payload["confidence"]), 2)
        return payload


@dataclass
class ScanResult:
    scan_id: str
    repository: str
    timestamp: str
    bugs: list[dict[str, Any]]
    status: str = "completed"
    severity: dict[str, int] | None = None
    files_scanned: int = 0
    ignored_files: int = 0
    scan_duration_seconds: float = 0.0
    language_breakdown: dict[str, int] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.severity is None:
            payload["severity"] = {}
        return payload
