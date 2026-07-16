# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-16

### Added
- **Proactive Repository Scanner**: Custom 9-phase static analysis scan loop detecting eval usages, raw SQL strings, broad exception clauses, and resource leaks.
- **Local AST Indexer**: AST-based python code parser (`src/indexer.py`) that maps top-level classes, methods, functions, constants, imports, and docstrings.
- **SaaS Glassmorphic Dashboard**: Modern Streamlit frontend design featuring live HTML progress bars, styled severity-coded finding cards, and active agent execution timeline tracking.
- **Git Push Conflict Resolution**: Auto-conflict workflow that checks remote branch existence before creating branches, and automatically renames and retries pushes if a non-fast-forward conflict is met.
- **Structured Pydantic Resolution Schema**: Enforced single-call prompt generation mapping analysis, patch files, pytest scripts, commit messages, and PR templates in JSON.
- **GitHub App Authentication**: JWT signature signing, automatic token refresh, accessible repo verification, and callback installation redirects.
- **Scan Store**: Asynchronous local JSON file persistence layer separating metadata indexes from findings payload data.
- **Browser Extension**: Manifest V3 extension supporting one-click repo detection and scanning from active GitHub tabs.

### Changed
- **Reasoning Loop redesign**: Replaced iterative "Think -> Search" loops with a deterministic local context-gathering pipeline followed by a one-shot LLM structured code patch generation (maximum 2-3 API calls).

### Improved
- **Token Logging**: Detailed logging for all OpenAI/OpenRouter and Gemini API calls capturing prompt and completion token counts.
- **Test Isolation**: Created global environment isolation via `tests/conftest.py` preventing developer API key leakage into unit mock tests.
- **PEM key path resolution**: Supports both absolute and root-relative file lookups for GitHub App private keys.

### Fixed
- **Scanner credentials detector**: Added target inspection in AST assignment node visitor (`visit_Assign`) to successfully detect variable string values assigned to keys like `api_key`.
- **Mock tests configuration**: Refactored assertion errors in webhook and pipeline mock tests to clean up execution leakage.

### Security
- **Webhook signing**: Validates requests with `X-Hub-Signature-256` HMAC hashes.
- **Token storage**: Secure internal memory caching for installation access tokens.
- **Path sandboxing**: Restricted repo workspace checkouts within workspace directories.

### Known Limitations
- Runs local unit tests inside subprocesses without Docker/gVisor virtualization.
- Source code analysis is restricted to Python files; other extension formats are keyword-matched.
