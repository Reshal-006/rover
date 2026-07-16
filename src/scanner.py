from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from src.scan_models import BugFinding, ScanResult
from src.ranking import rank_findings

SUPPORTED_EXTENSIONS = {'.py', '.js', '.ts', '.tsx', '.jsx', '.json', '.yaml', '.yml', '.md'}
IGNORED_DIRS = {'.git', 'venv', 'node_modules', 'dist', 'build', 'coverage', '__pycache__'}


def validate_repository_url(repository_url: str) -> bool:
    pattern = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?$")
    return bool(pattern.match(repository_url.strip()))


def clone_repository(repository_url: str, destination: str | None = None) -> str:
    if not validate_repository_url(repository_url):
        raise ValueError("Invalid GitHub repository URL")

    target = destination or os.path.join(tempfile.gettempdir(), "rover_scan", hashlib.md5(repository_url.encode()).hexdigest())
    os.makedirs(os.path.dirname(target), exist_ok=True)

    if os.path.exists(target):
        shutil.rmtree(target)

    subprocess.run(["git", "clone", repository_url, target], check=True, capture_output=True, text=True)
    return target


def _iter_source_files(root: str) -> list[Path]:
    files: list[Path] = []
    for current_root, dirs, filenames in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for filename in filenames:
            path = Path(current_root, filename)
            if path.suffix.lower() in SUPPORTED_EXTENSIONS and not path.is_symlink():
                files.append(path)
    return sorted(files)


def _run_bandit(files: list[Path]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path in files:
        if path.suffix.lower() != '.py':
            continue
        try:
            subprocess.run(["bandit", "-r", str(path), "-f", "json"], check=False, capture_output=True, text=True)
        except FileNotFoundError:
            continue
    return results


def _add_finding(findings: list[dict[str, Any]], key: tuple[str, int, str], data: dict[str, Any]) -> None:
    if key not in { (f['file'], f['line_number'], f['bug_type']) for f in findings }:
        findings.append(data)


def _find_python_issues(text: str, path: Path, findings: list[dict[str, Any]]) -> None:
    try:
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in {'eval', 'exec'}:
                    _add_finding(findings, (str(path), getattr(node, 'lineno', 1), 'Unsafe eval'), {
                        'file': str(path),
                        'line_number': getattr(node, 'lineno', 1),
                        'severity': 'high',
                        'bug_type': 'Unsafe eval',
                        'title': f'Use of {node.func.id}() in Python',
                        'description': 'Dynamic evaluation can execute arbitrary code and is a security risk.',
                        'confidence': 0.95,
                    })
                if node.func.id in {'open', 'subprocess'} and 'shell=True' in text:
                    _add_finding(findings, (str(path), getattr(node, 'lineno', 1), 'Command injection'), {
                        'file': str(path),
                        'line_number': getattr(node, 'lineno', 1),
                        'severity': 'high',
                        'bug_type': 'Command injection',
                        'title': 'Subprocess call with shell=True',
                        'description': 'Using shell=True can allow command injection if untrusted input is used.',
                        'confidence': 0.88,
                    })
            if isinstance(node, ast.ExceptHandler):
                if any(isinstance(child, ast.Pass) for child in node.body):
                    _add_finding(findings, (str(path), getattr(node, 'lineno', 1), 'Unhandled exception'), {
                        'file': str(path),
                        'line_number': getattr(node, 'lineno', 1),
                        'severity': 'medium',
                        'bug_type': 'Unhandled exception',
                        'title': 'Broad exception handling hides errors',
                        'description': 'Catching exceptions and passing through can hide bugs and prevent proper error handling.',
                        'confidence': 0.75,
                    })
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == 'random' and node.attr == 'random':
                _add_finding(findings, (str(path), getattr(node, 'lineno', 1), 'Weak randomness'), {
                    'file': str(path),
                    'line_number': getattr(node, 'lineno', 1),
                    'severity': 'low',
                    'bug_type': 'Weak randomness',
                    'title': 'Use of random.random()',
                    'description': 'The random module is not suitable for cryptographic secrets or strong randomness.',
                    'confidence': 0.65,
                })
    except SyntaxError:
        pass


def _find_javascript_issues(text: str, path: Path, findings: list[dict[str, Any]]) -> None:
    if re.search(r"\beval\s*\(", text):
        _add_finding(findings, (str(path), 1, 'Unsafe eval'), {
            'file': str(path),
            'line_number': 1,
            'severity': 'high',
            'bug_type': 'Unsafe eval',
            'title': 'Use of eval() in JavaScript',
            'description': 'Dynamic evaluation in JavaScript can execute arbitrary code and is a security risk.',
            'confidence': 0.92,
        })
    if re.search(r"new\s+Function\s*\(", text):
        _add_finding(findings, (str(path), 1, 'Unsafe eval'), {
            'file': str(path),
            'line_number': 1,
            'severity': 'high',
            'bug_type': 'Unsafe eval',
            'title': 'Dynamic function constructor usage',
            'description': 'new Function() executes strings as code and can be exploitable.',
            'confidence': 0.9,
        })
    if re.search(r"\binnerHTML\b|\bdocument\.write\b", text):
        _add_finding(findings, (str(path), 1, 'Security issue'), {
            'file': str(path),
            'line_number': 1,
            'severity': 'high',
            'bug_type': 'Security issue',
            'title': 'Direct DOM injection',
            'description': 'Setting innerHTML or document.write() can introduce cross-site scripting vulnerabilities.',
            'confidence': 0.84,
        })
    if re.search(r"Math\.random\s*\(", text):
        _add_finding(findings, (str(path), 1, 'Weak randomness'), {
            'file': str(path),
            'line_number': 1,
            'severity': 'low',
            'bug_type': 'Weak randomness',
            'title': 'Use of Math.random()',
            'description': 'Math.random() is not suitable for cryptographic or security-sensitive randomness.',
            'confidence': 0.7,
        })


def _find_generic_issues(text: str, path: Path, findings: list[dict[str, Any]]) -> None:
    secret_pattern = re.compile(r"(?:password|passwd|pwd|secret|api[_-]?key|token|auth)\s*[:=]\s*['\"][^'\"]+['\"]", re.I)
    if secret_pattern.search(text):
        _add_finding(findings, (str(path), 1, 'Hardcoded secret'), {
            'file': str(path),
            'line_number': 1,
            'severity': 'medium',
            'bug_type': 'Hardcoded secret',
            'title': 'Hardcoded credential or secret',
            'description': 'A literal secret or credential appears in the file.',
            'confidence': 0.8,
        })

    if re.search(r"\b(TODO|FIXME|HACK)\b", text):
        _add_finding(findings, (str(path), 1, 'Code smell'), {
            'file': str(path),
            'line_number': 1,
            'severity': 'low',
            'bug_type': 'Code smell',
            'title': 'Commented TODO/FIXME/HACK',
            'description': 'This file contains a developer note that may indicate incomplete or risky code.',
            'confidence': 0.6,
        })


def scan_file(filepath: str) -> list[dict[str, Any]]:
    path = Path(filepath)
    findings: list[dict[str, Any]] = []
    if not path.exists():
        return findings

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings

    suffix = path.suffix.lower()
    if suffix == '.py':
        _find_python_issues(text, path, findings)
    elif suffix in {'.js', '.jsx', '.ts', '.tsx'}:
        _find_javascript_issues(text, path, findings)
    elif suffix in {'.json', '.yaml', '.yml'}:
        _find_generic_issues(text, path, findings)
    elif suffix == '.md':
        _find_generic_issues(text, path, findings)

    # Generic checks apply to all supported files
    _find_generic_issues(text, path, findings)
    return findings


def scan_repository(repository_url: str, destination: str | None = None) -> dict[str, Any]:
    start = time.time()
    repo_path = clone_repository(repository_url, destination)
    files = _iter_source_files(repo_path)
    findings: list[dict[str, Any]] = []
    for path in files:
        findings.extend(scan_file(str(path)))

    language_breakdown: dict[str, int] = {}
    for path in files:
        suffix = path.suffix.lower().lstrip('.') or 'file'
        language_breakdown[suffix] = language_breakdown.get(suffix, 0) + 1

    ranked_findings = rank_findings(findings)
    severity_counts = {}
    for bug in ranked_findings:
        severity = str(bug.get("severity", "low")).lower()
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    result = ScanResult(
        scan_id=f"scan-{int(time.time())}",
        repository=repository_url,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        bugs=ranked_findings,
        status="completed",
        severity=severity_counts,
        files_scanned=len(files),
        ignored_files=0,
        scan_duration_seconds=round(time.time() - start, 2),
        language_breakdown=language_breakdown,
    )
    return result.to_dict()
