from __future__ import annotations

from typing import Any


_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
_IMPACT_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def rank_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str]] = set()

    # Normalize fields first
    normalized = []
    for f in findings:
        file = f.get("file") or f.get("filepath") or ""
        line = f.get("line_number") or f.get("line") or 1
        title = f.get("title") or f.get("bug_type") or ""
        severity = str(f.get("severity", "low")).lower()
        impact = str(f.get("impact", "low")).lower()
        
        # Support both float confidence (0.0-1.0) and int confidence (0-100)
        raw_conf = f.get("confidence")
        if raw_conf is None:
            confidence = 0.8
        else:
            try:
                val = float(raw_conf)
                if val > 1.0:
                    confidence = val / 100.0
                else:
                    confidence = val
            except Exception:
                confidence = 0.8

        item = dict(f)
        item["file"] = file
        item["filepath"] = file
        item["line_number"] = line
        item["title"] = title
        item["severity"] = severity
        item["impact"] = impact
        item["confidence"] = confidence
        normalized.append(item)

    # Sort key: severity (lower rank = higher priority), impact (lower rank = higher), -confidence
    def sort_key(item: dict[str, Any]) -> tuple[int, int, float, str, int]:
        sev = _SEVERITY_ORDER.get(item["severity"], 99)
        imp = _IMPACT_ORDER.get(item["impact"], 99)
        return sev, imp, -item["confidence"], item["file"], item["line_number"]

    # Deduplicate by key (file, line_number, title)
    for finding in sorted(normalized, key=sort_key):
        key = (finding["file"], finding["line_number"], finding["title"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(finding)

    return deduped
