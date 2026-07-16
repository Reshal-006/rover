# Rover Alpha Release Notes - v1.0.0

We are excited to announce the first public Alpha release of **Rover** (v1.0.0)! 🚀

Rover is a proactive, autonomous AI software engineer that scans your repositories, detects vulnerabilities and logic bugs, writes failing tests, generates fixes, and opens GitHub Pull Requests.

---

## What's New

### 1. Proactive Codebase Scanner
- Enters a 9-phase asynchronous background pipeline to clone, parse, and analyze repository source code.
- Custom AST static rules check for SQL injections, hardcoded credentials, eval statements, broad try-except blocks, and resource leaks.
- Integrated structured Gemini analysis filtering.

### 2. Streamlit Dashboard Refinement
- Glassmorphic SaaS aesthetic with Google Font Outfit typography.
- Tabbed history panel displaying both Agent Runs (Issue fixes) and Codebase Scans history.
- Visual HTML/CSS timeline tracking scan progress.
- Interactive bug findings cards with left-colored severity markers (Critical, High, Medium, Low) and quick "Fix Bug" actions.

### 3. Browser Extension
- Manifest V3 mini-extension that detects the active GitHub repository tab.
- Redirects with a single click to the local Streamlit dashboard to launch an auto-scan.

### 4. GitHub App Integration
- Complete token caching and automatic refresh flow.
- Seamless installation redirect callback.

---

## Limitations

- **Language Scope**: Currently supports Python repositories (`.py` files).
- **Test Isolation**: Runs test pipelines locally via subprocesses (non-sandboxed).
- **Storage Layer**: Local JSON file-based database.

---

## Future Enhancements

- **Multi-Language Parsing**: Integration of Tree-sitter for JS, Go, and Rust support.
- **Dockerized Sandboxing**: Run test pipelines in isolated, secure containers.
- **Multi-Agent Orchestration**: Separate roles for test writers and fix creators.
