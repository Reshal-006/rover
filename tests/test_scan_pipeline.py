import json
import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app
from src.ranking import rank_findings
from src.scanner import scan_file, scan_repository
from src.storage import ScanStore


def test_scan_file_detects_unsafe_eval(tmp_path):
    sample = tmp_path / "sample.py"
    sample.write_text("value = eval(user_input)\n", encoding="utf-8")

    findings = scan_file(str(sample))

    assert any(f["bug_type"] == "Unsafe eval" for f in findings)


def test_scan_file_detects_hardcoded_secret(tmp_path):
    sample = tmp_path / "config.yaml"
    sample.write_text("password: 's3cr3t'\n", encoding="utf-8")

    findings = scan_file(str(sample))

    assert any(f["bug_type"] == "Hardcoded secret" for f in findings)


def test_scan_file_detects_js_eval(tmp_path):
    sample = tmp_path / "script.js"
    sample.write_text("const value = eval(input);\n", encoding="utf-8")

    findings = scan_file(str(sample))

    assert any(f["bug_type"] == "Unsafe eval" for f in findings)


def test_scan_file_detects_todo_comment(tmp_path):
    sample = tmp_path / "README.md"
    sample.write_text("# TODO: add more checks\n", encoding="utf-8")

    findings = scan_file(str(sample))

    assert any(f["bug_type"] == "Code smell" for f in findings)


def test_rank_findings_deduplicates_and_sorts():
    findings = [
        {"file": "a.py", "line_number": 3, "severity": "low", "bug_type": "Logic bug", "confidence": 0.7},
        {"file": "a.py", "line_number": 3, "severity": "low", "bug_type": "Logic bug", "confidence": 0.95},
        {"file": "b.py", "line_number": 10, "severity": "high", "bug_type": "Security issue", "confidence": 0.9},
    ]

    ranked = rank_findings(findings)

    assert ranked[0]["file"] == "b.py"
    assert len(ranked) == 2


def test_storage_round_trip(tmp_path):
    store = ScanStore(base_dir=tmp_path)
    scan = {
        "scan_id": "scan-123",
        "repository": "https://github.com/example/demo",
        "status": "completed",
        "bugs": [{"title": "Demo bug", "severity": "medium"}],
    }

    store.save_scan(scan)
    loaded = store.load_scan("scan-123")

    assert loaded["scan_id"] == "scan-123"
    assert loaded["bugs"][0]["title"] == "Demo bug"


def test_scan_endpoint_returns_result(tmp_path, monkeypatch):
    client = TestClient(app)

    repo_path = tmp_path / "repo"
    (repo_path / "src").mkdir(parents=True, exist_ok=True)
    (repo_path / "src" / "sample.py").write_text("value = eval(user_input)\n", encoding="utf-8")

    monkeypatch.setattr("src.scanner.clone_repository", lambda repository_url, destination=None: str(repo_path))

    response = client.post(
        "/scan",
        json={"repository_url": "https://github.com/example/demo"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["repository"] == "https://github.com/example/demo"
    assert payload["bugs"]
