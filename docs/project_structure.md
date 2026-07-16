# Rover Project Structure

This document outlines the codebase layout and directory structure of Rover.

---

## 📂 Directory Tree

```
rover/
├── api/                   # FastAPI backend server
│   ├── __init__.py
│   └── main.py            # API routing, webhook parsing, scan orchestration
├── dashboard/             # Streamlit visual UI dashboard
│   ├── app.py             # Main UI loop, tabs configuration, and custom CSS
│   └── components/        # Reusable dashboard widgets
├── docs/                  # Project documentation guides
│   ├── adr/               # Architecture Decision Records (ADRs 001 - 012)
│   ├── api.md             # REST API specifications
│   ├── architecture.md    # System architecture flowcharts (Mermaid)
│   ├── deployment.md      # Docker, Render, and Streamlit Cloud configuration
│   ├── release_notes.md   # Release notes for version 1.0.0
│   ├── setup.md           # Onboarding and environment guide
│   └── testing.md         # pytest execution and mock conftest guide
├── extension/             # Manifest V3 browser extension
│   ├── manifest.json
│   ├── popup.html
│   └── popup.js           # Extracts repository URL and redirects to dashboard
├── logs/                  # Execution trace summaries and runs history logs
├── scans/                 # Local persistence layer storing scans & resolution caches
├── src/                   # Core business logic layer
│   ├── agent.py           # Resolution reasoning loop & git push conflict handlers
│   ├── github_auth.py     # GitHub App authentication & installations token caching
│   ├── github_client.py   # PyGithub wrapper (issues, branches, pull requests)
│   ├── indexer.py         # AST parser mapping codebase symbols
│   ├── llm.py             # LLM provider wrapper with automatic client fallbacks
│   ├── ranking.py         # Bug severity scoring and ranking heuristics
│   ├── scanner.py         # 9-phase proactive code Traversal and static analyzer
│   ├── storage.py         # ScanStore interface for saving repository findings
│   └── tools.py           # Subprocess commands (pytest runner, file editor)
├── tests/                 # Unit and integration test suites
│   ├── conftest.py        # Global mock environment isolation hooks
│   └── test_*.py          # Pytest files
├── .env.example           # Configuration variables template
├── CHANGELOG.md           # Commit history and changelog following "Keep a Changelog"
├── CONTRIBUTING.md        # Guidelines for submitting features & PRs
├── DEMO.md                # 5-minute showcase demo script
├── ROADMAP.md             # Multi-release future enhancement milestones
└── SECURITY.md            # App auth validation, webhook signing, and safety policy
```

---

## 🔍 Key Directory Descriptions

### 1. `api/`
Houses the FastAPI endpoints. Serves as the web entrance: handles GitHub webhook delivery triggers (`POST /webhook`) and serves asynchronous scans to the frontend.

### 2. `dashboard/`
Implements the Streamlit-based UI. Renders a tabbed interface containing scan findings cards, severity badges, and interactive run consoles.

### 3. `src/`
The functional core of the application:
- **`scanner.py`**: Executes static parsing rules.
- **`agent.py`**: Controls the fixing logic. Uses `indexer.py` to compile local context.
- **`github_auth.py`**: Handles PEM private keys to generate JWTs.

### 4. `tests/`
Validates component integrity. Ensures all API endpoints, auth token cache layers, and index parsing utilities function cleanly.
