from __future__ import annotations

from typing import Any


_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def rank_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str]] = set()

    def sort_key(item: dict[str, Any]) -> tuple[int, float, str, int]:
        severity = str(item.get("severity", "")).lower()
        severity_rank = _SEVERITY_ORDER.get(severity, 99)
        confidence = float(item.get("confidence", 0.0))
        return severity_rank, -confidence, str(item.get("file", "")), int(item.get("line_number", 0))

    for finding in sorted(findings, key=sort_key):
        key = (finding.get("file", ""), int(finding.get("line_number", 0)), finding.get("bug_type", ""))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(finding)

    return deduped
