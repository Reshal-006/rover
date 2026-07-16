# Rover Production Release Notes - v1.0.0

We are excited to announce the production release of **Rover** (v1.0.0)! 🚀

Rover is a proactive, autonomous AI software engineer that scans your repositories, detects vulnerabilities and logic bugs, builds local AST indexes, writes unit tests, generates fixes, and opens GitHub Pull Requests.

---

## 🌟 Key Highlights

### 1. "Analyze ➔ Gather Context ➔ Solve" Pipeline
- Redesigned the agent reasoning loop to eliminate wasteful token spend.
- The agent does not loop querying the LLM for search results. It builds a local AST symbol index, identifies target files using stack trace and keyword searches, collects code context locally, and runs a single LLM structured call.
- Reduces API consumption from **15–20+ calls per bug to a maximum of 2–3**.

### 2. Self-Healing Git Push Workflow
- Dynamic unique branch name generation: `rover/fix-issue-{issue_number}-{timestamp}-{short_uuid}`.
- Automated check on the remote GitHub ref before branch creation.
- Smart conflict resolution: If a git push fails (due to non-fast-forward rejection), the agent re-registers a new remote branch ref, renames the local branch using `git branch -m`, and pushes again without user intervention.

### 3. Glassmorphic Streamlit Dashboard
- Outfitted with sleek glassmorphism styling and custom HTML/CSS timelines.
- Separated tabs for **Scan History** (proactive discovery) and **Fix History** (reactive agent runs).
- Dynamic card indicators representing Critical, High, Medium, and Low severity bugs.

### 4. Codebase Indexer
- Crawls codebases and parses symbols (classes, methods, functions, imports, constants, docstrings) using native AST parsing.
- Implements timestamps and sizes verification to load from local cache (`.rover_index.json`) and bypass re-indexing.

---

## ⚠️ Limitations & Notes

- **Language Scope**: AST symbol parsing is native to Python (`.py` files). Other text files are keyword-matched.
- **Docker Isolation**: Code validations are run locally using subprocesses. Dockerized sandboxing is planned for **v1.1.0**.
- **Database**: Local JSON persistence using the `ScanStore` interface.

---

## 🔮 Future Enhancements

- **v1.1.0**: Tree-sitter multi-language integration, Dockerized test execution.
- **v1.2.0**: Multi-agent orchestrator loops (Critic, Architect, Validator models).
- **v2.0.0**: Deep semantic search using vector embedding databases.
