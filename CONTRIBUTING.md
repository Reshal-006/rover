# Contributing to Rover

Thank you for your interest in contributing to Rover! Follow this guide to get set up for local development, run tests, and open pull requests.

---

## 🛠️ Local Development Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Reshal-006/rover.git
cd rover
```

### 2. Set Up Virtual Environment
Create a virtual environment and install development dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-cov
```

### 3. Environment Variables
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```
For local testing without a GitHub App, you can configure classic `GITHUB_TOKEN` credentials and turn `USE_GITHUB_APP=false`.

---

## 🧪 Testing Guidelines

We use `pytest` for unit and integration testing.

### Running Tests
To run the full suite:
```bash
pytest
```

### Environment Isolation
Our test suite uses `tests/conftest.py` to automatically isolate environment variables. This prevents local keys (like `GITHUB_INSTALLATION_ID`) from leaking into mock tests. If you write new tests requiring custom mock environments, use `monkeypatch` to set or delete temporary values.

---

## 💻 Coding Standards

- **Formatting**: We follow standard Python PEP 8 conventions. Use a formatter like `black` or `autopep8`.
- **Typing**: Use static typing hints where appropriate.
- **Logging**: Use Rover's standard logger (`logging.getLogger("rover")`) instead of bare `print` statements.

---

## 📥 Submitting Pull Requests

1. **Create a branch** named `feature/your-feature-name` or `bugfix/your-fix-name`.
2. **Write clean commits** with meaningful commit messages.
3. **Ensure tests pass** locally before pushing.
4. **Open a Pull Request** against the `main` branch. Provide a detailed summary of what your changes accomplish.
