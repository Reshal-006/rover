import json
from pathlib import Path
import pytest
from src.scanner import ASTScanner, run_ast_scanner, traverse_repo, is_binary
from src.ranking import rank_findings
from src.storage import ScanStore


def test_is_binary(tmp_path):
    text_file = tmp_path / "text.txt"
    text_file.write_text("Hello World", encoding="utf-8")
    assert not is_binary(text_file)

    binary_file = tmp_path / "binary.bin"
    binary_file.write_bytes(b"\x00\x01\x02\x03Hello")
    assert is_binary(binary_file)


def test_traverse_repo(tmp_path):
    # Set up a mock repo structure
    repo_dir = tmp_path / "my_repo"
    repo_dir.mkdir()

    # Normal python file
    (repo_dir / "app.py").write_text("print('hello')", encoding="utf-8")

    # Ignored directory
    git_dir = repo_dir / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("some git config", encoding="utf-8")

    # Ignored venv
    venv_dir = repo_dir / "venv"
    venv_dir.mkdir()
    (venv_dir / "lib.py").write_text("some lib", encoding="utf-8")

    # Binary file
    (repo_dir / "data.png").write_bytes(b"\x00\x89PNG")

    discovered = traverse_repo(str(repo_dir))
    rel_paths = [f["relative_path"] for f in discovered]

    assert "app.py" in rel_paths
    assert ".git/config" not in rel_paths
    assert "venv/lib.py" not in rel_paths
    assert "data.png" not in rel_paths


def test_ast_scanner_rules():
    # 1. Test eval and exec
    code_eval = "eval('1+1')"
    findings = run_ast_scanner(code_eval, "app.py", "app.py")
    assert any("eval" in f["title"].lower() for f in findings)

    code_exec = "exec('x = 2')"
    findings = run_ast_scanner(code_exec, "app.py", "app.py")
    assert any("exec" in f["title"].lower() for f in findings)

    # 2. Test subprocess shell=True and os.system
    code_sub = "import subprocess\nsubprocess.run('ls', shell=True)"
    findings = run_ast_scanner(code_sub, "app.py", "app.py")
    assert any("shell=True" in f["description"] for f in findings)

    code_os = "import os\nos.system('ls')"
    findings = run_ast_scanner(code_os, "app.py", "app.py")
    assert any("os.system" in f["title"].lower() for f in findings)

    # 3. Test resource leaks (open without with)
    code_leak = "f = open('data.txt')\nf.read()"
    findings = run_ast_scanner(code_leak, "app.py", "app.py")
    assert any("file opened without with-context" in f["title"].lower() for f in findings)

    # 4. Test broad try/except pass
    code_try = "try:\n    x = 1/0\nexcept:\n    pass"
    findings = run_ast_scanner(code_try, "app.py", "app.py")
    assert any("broad exception clause" in f["title"].lower() for f in findings)

    # 5. Test SQL injection string
    code_sql = "query = 'SELECT * FROM users WHERE name = %s'"
    findings = run_ast_scanner(code_sql, "app.py", "app.py")
    assert any("sql query string" in f["title"].lower() for f in findings)

    # 6. Test hardcoded secrets
    code_secret = "api_key = 'sk-1234567890abcdef'"
    findings = run_ast_scanner(code_secret, "app.py", "app.py")
    assert any("hardcoded secret" in f["title"].lower() for f in findings)


def test_ranking_deduplication_and_sorting():
    findings = [
        {
            "file": "main.py",
            "line_number": 10,
            "title": "Use of eval()",
            "severity": "high",
            "impact": "high",
            "confidence": 0.9,
        },
        {
            "file": "main.py",
            "line_number": 10,
            "title": "Use of eval()",
            "severity": "high",
            "impact": "high",
            "confidence": 0.95,  # Duplicate of above but higher confidence
        },
        {
            "file": "utils.py",
            "line_number": 20,
            "title": "Division operation",
            "severity": "low",
            "impact": "low",
            "confidence": 0.5,
        },
        {
            "file": "auth.py",
            "line_number": 5,
            "title": "Hardcoded secret",
            "severity": "critical",
            "impact": "critical",
            "confidence": 0.99,
        },
    ]

    ranked = rank_findings(findings)

    # deduplicated length should be 3 (one of the main.py line 10 eval findings is removed)
    assert len(ranked) == 3

    # The critical severity should be ranked first
    assert ranked[0]["file"] == "auth.py"
    # The low severity should be ranked last
    assert ranked[-1]["file"] == "utils.py"


def test_storage_separation(tmp_path):
    store = ScanStore(base_dir=str(tmp_path))
    scan_id = "scan-999"
    scan_data = {
        "scan_id": scan_id,
        "repository": "https://github.com/user/project",
        "timestamp": "2026-07-16T12:00:00Z",
        "status": "completed",
        "bugs": [
            {"title": "Bug 1", "severity": "high", "confidence": 0.9},
            {"title": "Bug 2", "severity": "low", "confidence": 0.4}
        ]
    }

    store.save_scan(scan_data)

    # Verify files exist separately
    meta_file = tmp_path / f"{scan_id}.json"
    findings_file = tmp_path / f"{scan_id}_findings.json"

    assert meta_file.exists()
    assert findings_file.exists()

    # Verify content structure
    meta_content = json.loads(meta_file.read_text(encoding="utf-8"))
    assert "bugs" not in meta_content  # Stored separately
    assert meta_content["status"] == "completed"

    findings_content = json.loads(findings_file.read_text(encoding="utf-8"))
    assert len(findings_content) == 2
    assert findings_content[0]["title"] == "Bug 1"

    # Reload scan and ensure it's reassembled
    loaded = store.load_scan(scan_id)
    assert len(loaded["bugs"]) == 2
    assert loaded["bugs"][0]["title"] == "Bug 1"
    assert loaded["bugs"][1]["title"] == "Bug 2"
