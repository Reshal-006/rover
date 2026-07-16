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
        path = self.base_dir / f"{scan_id}.json"
        path.write_text(json.dumps(scan, indent=2), encoding="utf-8")
        return scan

    def load_scan(self, scan_id: str) -> dict[str, Any]:
        path = self.base_dir / f"{scan_id}.json"
        if not path.exists():
            raise FileNotFoundError(scan_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def list_scans(self) -> list[dict[str, Any]]:
        scans = []
        for path in sorted(self.base_dir.glob("*.json")):
            scans.append(json.loads(path.read_text(encoding="utf-8")))
        return scans
