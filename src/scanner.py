from __future__ import annotations

import ast
import hashlib
import json
import logging
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

logger = logging.getLogger("rover.scanner")

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

    USE_GITHUB_APP = os.getenv('USE_GITHUB_APP', 'false').lower() == 'true'
    url = repository_url
    if USE_GITHUB_APP:
        from src.github_auth import load_installation_id, get_installation_token, get_repo_installation
        repo_name = repository_url.replace('https://github.com/', '').rstrip('/')
        parts = repo_name.split('/')
        installation_id = None
        if len(parts) == 2:
            installation_id = get_repo_installation(parts[0], parts[1])
        if not installation_id:
            installation_id = load_installation_id()

        if installation_id:
            try:
                token = get_installation_token(installation_id)
                url = f'https://x-access-token:{token}@github.com/{repo_name}.git'
            except Exception as e:
                raise RuntimeError(f"Failed to retrieve installation token for repository scanning: {e}")
        else:
            raise RuntimeError("USE_GITHUB_APP is true but no GitHub App installation ID could be resolved for repository.")
    else:
        GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '').strip()
        if GITHUB_TOKEN:
            repo_name = repository_url.replace('https://github.com/', '').rstrip('/')
            url = f'https://{GITHUB_TOKEN}@github.com/{repo_name}.git'

    subprocess.run(["git", "clone", url, target], check=True, capture_output=True, text=True)
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


def is_binary(file_path: Path) -> bool:
    """Check if a file is binary by searching for null bytes in the first chunk."""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            return b'\0' in chunk
    except Exception:
        return True


def traverse_repo(repo_path: str) -> list[dict[str, Any]]:
    """Walk the repository recursively and collect supported code files."""
    discovered_files = []
    ignored_dirs = {'.git', 'venv', '__pycache__', 'node_modules', 'dist', 'build', 'coverage'}
    for current_root, dirs, filenames in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith('venv')]
        for filename in filenames:
            full_path = Path(current_root, filename)
            if full_path.is_symlink():
                continue
            
            parts = full_path.parts
            if any(p in ignored_dirs or p.startswith('venv') for p in parts):
                continue
                
            if is_binary(full_path):
                continue
                
            if full_path.suffix.lower() == '.py':
                rel_path = str(full_path.relative_to(repo_path))
                discovered_files.append({
                    'filepath': str(full_path),
                    'relative_path': rel_path,
                    'extension': full_path.suffix.lower(),
                    'size': full_path.stat().st_size
                })
    return discovered_files


class ASTScanner(ast.NodeVisitor):
    def __init__(self, filepath: str, source_code: str, relative_path: str):
        self.filepath = filepath
        self.source_code = source_code
        self.relative_path = relative_path
        self.findings = []
        self.lines = source_code.splitlines()
        self.in_with = False

    def add_finding(self, node, category, title, description, severity="medium", confidence=0.8, impact="medium"):
        line = getattr(node, 'lineno', 1)
        code_snippet = ""
        if 0 < line <= len(self.lines):
            code_snippet = self.lines[line - 1].strip()
        self.findings.append({
            'file': self.relative_path,
            'filepath': self.relative_path,
            'line_number': line,
            'bug_type': category,
            'title': title,
            'description': description,
            'severity': severity,
            'confidence': confidence,
            'impact': impact,
            'code_snippet': code_snippet,
            'category': category,
            'reasoning': description,
            'suggested_fix': f"# Review implementation around line {line}"
        })

    def visit_Call(self, node):
        # 1. eval()
        if isinstance(node.func, ast.Name) and node.func.id == 'eval':
            self.add_finding(node, "Security", "Use of eval() in Python", "eval() can execute arbitrary code and is a security risk.", "high", 0.95, "high")
        # 2. exec()
        elif isinstance(node.func, ast.Name) and node.func.id == 'exec':
            self.add_finding(node, "Security", "Use of exec() in Python", "exec() can execute arbitrary code and is a security risk.", "high", 0.95, "high")
        # 3. os.system()
        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == 'os' and node.func.attr == 'system':
            self.add_finding(node, "Security", "Use of os.system()", "os.system() is deprecated and vulnerable to command injection.", "high", 0.9, "high")
        # 4. subprocess shell=True
        elif (isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == 'subprocess') or \
             (isinstance(node.func, ast.Name) and node.func.id == 'subprocess'):
            for kw in node.keywords:
                if kw.arg == 'shell':
                    if (isinstance(kw.value, ast.Constant) and kw.value.value is True) or \
                       (isinstance(kw.value, ast.Name) and kw.value.id == 'True'):
                        self.add_finding(node, "Security", "Subprocess call with shell=True", "Using shell=True can allow command injection if untrusted input is passed.", "high", 0.9, "high")

        # 5. Resource leaks: open() without with
        if isinstance(node.func, ast.Name) and node.func.id == 'open':
            if not self.in_with:
                self.add_finding(node, "Code Smell", "File opened without with-context", "Opening a file without a 'with' statement can lead to resource leaks if not closed properly.", "medium", 0.7, "medium")

        self.generic_visit(node)

    def visit_With(self, node):
        self.in_with = True
        self.generic_visit(node)
        self.in_with = False

    def visit_BinOp(self, node):
        # 6. division
        if isinstance(node.op, ast.Div):
            if isinstance(node.right, ast.Constant) and node.right.value == 0:
                self.add_finding(node, "Logic", "Division by zero", "Division by constant zero detected, which will crash at runtime.", "critical", 0.99, "high")
            else:
                self.add_finding(node, "Reliability", "Division operation", "Division operation detected. Ensure denominator is non-zero.", "low", 0.5, "low")
        self.generic_visit(node)

    def visit_Subscript(self, node):
        # 7. indexing
        self.add_finding(node, "Reliability", "Indexing operation", "Array or dict indexing operation; verify bounds or key existence.", "low", 0.5, "low")
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        # 8. try/except broad exception or empty pass
        has_pass = any(isinstance(stmt, ast.Pass) for stmt in node.body)
        if has_pass:
            self.add_finding(node, "Code Smell", "Broad exception clause with pass", "Catching exceptions and passing silently can hide critical bugs.", "medium", 0.8, "medium")
        self.generic_visit(node)

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            val = node.value
            # 9. SQL query strings
            sql_keywords = ["select ", "insert ", "update ", "delete ", "drop table"]
            if any(kw in val.lower() for kw in sql_keywords) and "from" in val.lower():
                self.add_finding(node, "Security", "Potential raw SQL query string", "Raw SQL query string detected; ensure parameters are parameterized to prevent SQL Injection.", "medium", 0.6, "high")
            
            # 10. Hardcoded secrets
            secret_keywords = ["password", "secret", "token", "api_key", "passwd", "pwd"]
            if any(sk in val.lower() for sk in secret_keywords) and len(val) > 6:
                self.add_finding(node, "Security", "Potential hardcoded secret value", "Potential hardcoded credential or secret detected.", "high", 0.7, "high")
        self.generic_visit(node)

    def visit_Assign(self, node):
        # Check target names for secret keywords
        is_secret_var = False
        secret_keywords = ["password", "secret", "token", "api_key", "passwd", "pwd"]
        for target in node.targets:
            if isinstance(target, ast.Name):
                if any(sk in target.id.lower() for sk in secret_keywords):
                    is_secret_var = True
            elif isinstance(target, ast.Attribute):
                if any(sk in target.attr.lower() for sk in secret_keywords):
                    is_secret_var = True
                    
        if is_secret_var and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            val = node.value.value
            if len(val) > 4:  # Non-trivial string length
                self.add_finding(node, "Security", "Potential hardcoded secret value", "Potential hardcoded credential or secret detected.", "high", 0.7, "high")
        self.generic_visit(node)



def run_ast_scanner(text: str, filepath: str, relative_path: str) -> list[dict[str, Any]]:
    """Parse text AST and run scanner rules."""
    try:
        tree = ast.parse(text)
        scanner = ASTScanner(filepath, text, relative_path)
        scanner.visit(tree)
        return scanner.findings
    except Exception:
        return []


def analyze_file_with_llm(filepath: str, relative_path: str, content: str, static_findings: list[dict]) -> list[dict]:
    """Ask LLM to perform deep logic/category analysis on the file content."""
    if not content.strip():
        return []

    # Limit size to prevent token count overflow
    if len(content) > 15000:
        content = content[:15000] + "\n... [TRUNCATED]"

    from src.llm import call_llm_structured, LLMBugAnalysisResponse
    
    prompt = f"""
Analyze the following source code file for potential bugs.
File Path: {relative_path}

Lightweight Static Analysis Findings:
{json.dumps(static_findings, indent=2)}

File Content:
```python
{content}
```

Identify any real bugs in this file (e.g. logic errors, security vulnerabilities, reliability issues, performance bottlenecks, code smells, or maintainability issues).
You must output a JSON object matching the requested schema. You can confirm or discard the static analysis findings, and add any other findings you discover.
Provide title, description, severity (low, medium, high, critical), confidence (0.0 to 1.0), category (Security, Logic, Performance, Reliability, Code Smell, Maintainability), filepath (must match '{relative_path}'), line_number, code_snippet, reasoning, suggested_fix, and impact (low, medium, high, critical).
"""
    try:
        result_text = call_llm_structured(prompt, LLMBugAnalysisResponse)
        if result_text:
            data = json.loads(result_text)
            findings = data.get("findings", [])
            
            # Normalize findings
            normalized = []
            for f in findings:
                f["file"] = relative_path
                f["filepath"] = relative_path
                normalized.append(f)
            return normalized
    except Exception as e:
        logger.error("LLM analysis failed for file %s: %s", relative_path, e)
    return []


def scan_repository(repository_url: str, destination: str | None = None, scan_id: str | None = None) -> dict[str, Any]:
    """Execute the full progress-reporting repository scanner workflow."""
    from src.storage import ScanStore
    
    start_time = time.time()
    store = ScanStore()
    
    if not scan_id:
        scan_id = f"scan-{int(start_time)}"

    def update_progress(phase: str, progress: int, files_scanned: int = 0, current_file: str = "", status: str = "scanning", bugs: list = None, error: str = None):
        try:
            data = store.load_scan(scan_id)
        except Exception:
            data = {
                "scan_id": scan_id,
                "repository": repository_url,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "status": status,
                "bugs": [],
                "files_scanned": 0,
                "ignored_files": 0,
                "scan_duration_seconds": 0
            }
        data["phase"] = phase
        data["progress"] = progress
        data["files_scanned"] = files_scanned
        data["current_file"] = current_file
        data["status"] = status
        if bugs is not None:
            data["bugs"] = bugs
        if error is not None:
            data["error"] = error
        store.save_scan(data)

    try:
        # Phase 1: Cloning
        update_progress("cloning", 10, current_file="Cloning repository...")
        repo_path = clone_repository(repository_url, destination)
        logger.info("Repository cloned: %s", repository_url)

        # Build symbol table index once per scan and cache it
        try:
            from src.indexer import RepositoryIndexer
            indexer = RepositoryIndexer(repo_path)
            indexer.get_index()
        except Exception as e:
            logger.warning("Failed to build repository index cache: %s", e)

        # Phase 2: Traversal / Discovery
        update_progress("traversal", 20, current_file="Discovering files...")
        discovered = traverse_repo(repo_path)
        logger.info("Files discovered: %d", len(discovered))

        # Phase 3: Static Analysis
        update_progress("static_analysis", 30, current_file="Running static analysis...")
        findings = []
        
        python_files = [f for f in discovered if f['extension'] == '.py']
        
        for idx, f in enumerate(python_files):
            rel = f['relative_path']
            full = f['filepath']
            update_progress("static_analysis", int(30 + (idx / max(len(python_files), 1)) * 20), len(python_files), current_file=f"Static analysis: {rel}")
            try:
                text = Path(full).read_text(encoding="utf-8", errors="ignore")
                static_f = run_ast_scanner(text, full, rel)
                findings.extend(static_f)
            except Exception as e:
                logger.error("Failed static analysis for %s: %s", rel, e)
                
        logger.info("Static analysis completed")

        # Phase 4: LLM Analysis
        update_progress("llm_analysis", 50, len(python_files), current_file="Running LLM bug analysis...")
        llm_findings = []
        for idx, f in enumerate(python_files):
            rel = f['relative_path']
            full = f['filepath']
            update_progress("llm_analysis", int(50 + (idx / max(len(python_files), 1)) * 35), len(python_files), current_file=f"LLM analysis: {rel}")
            try:
                text = Path(full).read_text(encoding="utf-8", errors="ignore")
                file_static = [sf for sf in findings if sf.get('file') == rel]
                file_llm = analyze_file_with_llm(full, rel, text, file_static)
                llm_findings.extend(file_llm)
            except Exception as e:
                logger.error("Failed LLM analysis for %s: %s", rel, e)
                
        logger.info("LLM analysis completed")

        # Combine findings
        all_findings = findings + llm_findings

        # Phase 5: Ranking
        update_progress("ranking", 90, len(python_files), current_file="Ranking findings...")
        ranked_findings = rank_findings(all_findings)
        logger.info("Ranking completed")

        # Group counts
        severity_counts = {}
        for bug in ranked_findings:
            severity = str(bug.get("severity", "low")).lower()
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        language_breakdown = {}
        for f in discovered:
            ext = f['extension'].lstrip('.') or 'file'
            language_breakdown[ext] = language_breakdown.get(ext, 0) + 1

        duration = round(time.time() - start_time, 2)
        result = {
            "scan_id": scan_id,
            "repository": repository_url,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "bugs": ranked_findings,
            "status": "completed",
            "severity": severity_counts,
            "files_scanned": len(python_files),
            "ignored_files": len(discovered) - len(python_files),
            "scan_duration_seconds": duration,
            "language_breakdown": language_breakdown,
            "phase": "completed",
            "progress": 100,
            "current_file": ""
        }
        
        store.save_scan(result)
        return result
    except Exception as exc:
        logger.error("Scan failed: %s", exc)
        update_progress("failed", 100, status="failed", error=str(exc))
        raise
