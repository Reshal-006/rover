# Rover Testing Guide

This document describes how to execute tests, generate coverage reports, and configure mock environments for development.

---

## 🧪 Running Unit Tests

We use `pytest` for codebase test execution.

### Run All Tests
```bash
pytest
```

### Run Specific Test File
```bash
pytest tests/test_indexer.py
```

### Verbose Execution
```bash
pytest -v
```

---

## 🛡️ Test Environment Isolation

To prevent local developer environment variables (such as active `GITHUB_INSTALLATION_ID` or `GITHUB_PRIVATE_KEY` set in your `.env` file) from bleeding into mock tests, we configure a global test environment cleanup inside `tests/conftest.py`.

### How it works:
Before any test executes, `conftest.py` purges active auth variables from `os.environ` and overrides credentials settings:
```python
import os
import pytest

@pytest.fixture(autouse=True)
def isolate_test_environment(monkeypatch):
    # Delete active variables to isolate mock testing environment
    monkeypatch.delenv("GITHUB_INSTALLATION_ID", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("USE_GITHUB_APP", "false")
```

If you are writing new tests that require specific mock tokens or credentials, use the `monkeypatch` fixture directly within your test function to set them safely.

---

## 📊 Coverage Analysis

You can generate test coverage metrics using `pytest-cov`:

```bash
# Run tests and output text coverage report
pytest --cov=src --cov=api --cov-report=term-missing
```

---

## 📲 Manual & Integration Testing

To manually test the complete agent fix loop without setting up webhooks:
1. Fork `rover-demo-repo` (which contains simple target bugs).
2. Install the GitHub App on your fork.
3. Open an issue on your fork (e.g., "Fix DivisionByZero error") and add the label `rover`.
4. Trigger the backend manually, or run:
   ```bash
   python -c "from src.agent import run_agent_for_issue; run_agent_for_issue('your-username/rover-demo-repo', <issue_number>)"
   ```
5. Verify the PR is successfully generated and pushed.
