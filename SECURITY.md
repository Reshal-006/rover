# Security Policy

This document outlines the security architecture, authentication methods, credential handling, and limitations of Rover.

---

## 🔑 GitHub App Authentication

Rover uses **GitHub Apps** to interact with repositories instead of high-privilege Personal Access Tokens (PATs). 

### How it Works:
```
[Rover Agent] ➔ Signs JWT with GITHUB_PRIVATE_KEY
                  ↓
[GitHub API]  ➔ Validates JWT, returns installation access token
                  ↓
[Rover Agent] ➔ Caches token in memory, refreshes on expiry (1 hour)
```

- **JWT Lifetime**: Generated dynamically with an expiration of 10 minutes to verify authentication.
- **Access Scope**: Scoped strictly to the specific repositories where the GitHub App is installed.
- **Token Cache**: Access tokens are kept in-memory and are never written to disk.

---

## 🛡️ Webhook Validation

FastAPI endpoints that receive events from GitHub (e.g., `POST /webhook`) validate payloads using HMAC-SHA256 signatures:

1. GitHub signs the payload using the `WEBHOOK_SECRET` configuration variable.
2. Rover intercepts the payload and recalculates the signature using `hmac.compare_digest`.
3. If signatures do not match, Rover returns a `403 Forbidden` status immediately, preventing unauthorized event injection.

---

## 📂 Private Key Management

- **PEM Storage**: The App's private key (`.pem` format) must be stored in the root workspace or referenceable path.
- **Environment Reference**: `GITHUB_PRIVATE_KEY` points to the file location. Key files are ignored by version control via `.gitignore`.

---

## ⚠️ Sandboxing & Execution Risks

> [!WARNING]
> Rover runs code validation tests (e.g. `pytest`) locally on the host machine using Python subprocesses. It does **not** yet execute code in virtualized/containerized sandboxes (like Docker or gVisor). 
> 
> Only run Rover on repositories that you fully trust. Running Rover on malicious repositories could lead to arbitrary code execution on your host system. Sandboxed execution is planned for **v1.1.0**.
