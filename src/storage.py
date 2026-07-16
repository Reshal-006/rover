from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class ScanStore:
    def __init__(self, base_dir: str | None = None):
        self.base_dir = Path(base_dir or os.path.join(os.getcwd(), "scans"))
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_scan(self, scan: dict[str, Any]) -> dict[str, Any]:
        scan_id = str(scan.get("scan_id") or "scan")
        
        # Extract findings to save separately
        # Make a copy of scan metadata without full bugs list
        meta = {k: v for k, v in scan.items() if k != "bugs"}
        findings = scan.get("bugs", [])
        
        # Save metadata
        meta_path = self.base_dir / f"{scan_id}.json"
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        
        # Save findings separately
        findings_path = self.base_dir / f"{scan_id}_findings.json"
        findings_path.write_text(json.dumps(findings, indent=2), encoding="utf-8")
        
        return scan

    def load_scan(self, scan_id: str) -> dict[str, Any]:
        meta_path = self.base_dir / f"{scan_id}.json"
        if not meta_path.exists():
            raise FileNotFoundError(scan_id)
        
        scan = json.loads(meta_path.read_text(encoding="utf-8"))
        
        # Re-attach findings if available
        findings_path = self.base_dir / f"{scan_id}_findings.json"
        if findings_path.exists():
            try:
                scan["bugs"] = json.loads(findings_path.read_text(encoding="utf-8"))
            except Exception:
                scan["bugs"] = []
        else:
            scan["bugs"] = []
            
        return scan

    def list_scans(self) -> list[dict[str, Any]]:
        scans = []
        for path in sorted(self.base_dir.glob("*.json")):
            if path.name.endswith("_findings.json") or path.name.endswith("_progress.json"):
                continue
            try:
                scans.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                pass
        return scans
