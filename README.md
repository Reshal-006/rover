<div align="center">

<img src="docs/rover_banner.png" alt="Rover Banner" width="100%"/>

<br/>

# Rover

**Explores your code. Fixes what it finds.**

Rover is an autonomous AI agent that reads a GitHub bug report, navigates your codebase to locate the root cause, writes a failing test to prove the bug exists, applies a targeted fix, verifies it works, and opens a Pull Request — without any human involvement until the review stage.

</div>

---

## The Problem

Developers spend 20–30% of their time on debugging. Most of that time is spent on bugs that follow a completely predictable pattern — read the stack trace, find the file, write a test, apply a null check or boundary fix, confirm it passes. The same steps, every time, for hundreds of bugs a year.

Rover automates that pattern end to end.

---

## How It Works

```
Developer files a GitHub Issue
          │
          ▼
FastAPI webhook receives the event
          │
          ▼
Agent clones the repository
          │
          ▼
Gemini (Google GenAI) explores the codebase
  ├── search_code()   finds relevant files
  └── read_file()     reads the suspicious functions
          │
          ▼
Confidence check (0–100)
  ├── ≥ 50  →  proceed to fix
  └──  < 50  →  post clarifying question on the Issue
          │
          ▼
Agent writes a failing pytest test  (edit_file)
          │
          ▼
Agent applies a minimal fix  (edit_file)
          │
          ▼
Agent runs the test suite  (run_tests)
  ├── PASS  →  open Pull Request + post summary comment
  └── FAIL  →  revise hypothesis, retry (max 3 attempts)
```

---

**Filing a bug report:**

```
Title: Wrong password crashes the app instead of showing an error

When I call authenticate_user() with a username that does not exist in
the database, the function crashes with a KeyError instead of returning
'Invalid credentials'.

Steps to reproduce:
1. Call authenticate_user('nobody', 'anypassword')
2. Expected: return 'Invalid credentials'
3. Actual:   KeyError: 'password'
```

**What Rover does automatically:**

1. Searches the codebase for `password` and `authenticate`
2. Reads `src/auth.py` and identifies the missing null check
3. Writes `tests/test_auth.py` with a test that currently fails
4. Adds the null check to `authenticate_user()`
5. Runs pytest — test passes, no regressions
6. Opens a Pull Request with the fix and the new test
7. Posts a comment on the Issue explaining what it found

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        ROVER SYSTEM                         │
└─────────────────────────────────────────────────────────────┘

  GitHub Issue  ──►  FastAPI Webhook  ──►  Agent Orchestrator
  (labeled rover)     (api/main.py)        (src/agent.py)
                                                  │
                                     ┌────────────▼────────────┐
                                     │    Gemini (Google GenAI) (tool use)    │
                                     │  decides what to call   │
                                     └────────────┬────────────┘
                                                  │
                          ┌───────────────────────┼───────────────────────┐
                          │                       │                       │
                    read_file()           search_code()            edit_file()
                    run_tests()
                          │
                          ▼
              GitHub API  ──►  Comment on Issue  +  Open Pull Request
                          │
                          ▼
              Streamlit Dashboard  (run history, metrics, manual trigger)
```

---

## Tech Stack

| Component | Technology | Why |
|----------|-----------|-----|
| Language model | Gemini (Google GenAI) | Google GenAI (Gemini) via the `google-genai` SDK; supports function-like tooling and content generation |
| Agent orchestration | Python 3.11 (raw) | Full control over the loop; easier to debug than frameworks |
| Web server | FastAPI | Async, webhook-ready, auto-generates `/docs` |
| GitHub integration | PyGithub | Clean Python SDK for the GitHub REST API |
| Repository management | GitPython | Clone and manage repos programmatically |
| Test runner | pytest (subprocess) | Process isolation; return code 0 = pass |
| Dashboard | Streamlit | Run history + metrics + manual trigger |
| Deployment | Render + Streamlit Cloud | Free tier; GitHub-connected auto-deploy |
| Secret management | python-dotenv | `.env` locally, env vars in production |

---

## Quickstart

### Prerequisites

- Python 3.11+
- `GEMINI_API_KEY` (Google GenAI API key or credential) — see Google Cloud / GenAI docs for how to create API credentials
- [GitHub Personal Access Token](https://github.com/settings/tokens) with `repo` and `write:discussion` scopes

### Install

```bash
git clone https://github.com/Reshal-006/rover.git
cd rover
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # fill in your API keys (see Environment Variables below)
```

### Run the agent server

```bash
uvicorn api.main:app --reload --port 8000
```

The API docs are available at `http://localhost:8000/docs`.

### Run the dashboard

```bash
# in a separate terminal
streamlit run dashboard/app.py
```

### Run tests

```bash
pytest tests/ -v
```

### Test webhooks locally

```bash
ngrok http 8000
# use the printed HTTPS URL as your GitHub webhook payload URL
```

---

## Sending a Bug to Rover

1. Go to any repository that has Rover's webhook installed.
2. Open a new Issue.
3. Add the `rover` label.
4. Rover picks it up automatically.

For best results, the Issue description should include:
- What the expected behaviour is
- What actually happened (error message or wrong output)
- The function or file name if known

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```env
GEMINI_API_KEY=AQ...         # your Google GenAI API key or credential
GITHUB_TOKEN=ghp_...
WEBHOOK_SECRET=any-random-string-matching-your-webhook-settings
```

| Variable | Where to get it |
|---------|----------------|
| `GEMINI_API_KEY` | Google Cloud Console / GenAI credentials — create an API key or service account credential for the GenAI API |
| `GITHUB_TOKEN` | GitHub → Settings → Developer settings → Personal access tokens |
| `WEBHOOK_SECRET` | Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |

---

## Project Structure

```
rover/
├── src/
│   ├── agent.py          # reasoning loop — the brain
│   ├── tools.py          # read_file, search_code, edit_file, run_tests
│   ├── llm.py            # Google GenAI client + tool definitions + system prompt
│   ├── github_client.py  # GitHub API integration
│   └── utils.py          # logging helpers
├── api/
│   └── main.py           # FastAPI webhook listener
├── dashboard/
│   └── app.py            # Streamlit run-history dashboard
├── tests/
│   └── test_tools.py     # unit tests for the tool layer
├── docs/
│   ├── rover_banner.png
│   ├── architecture.png
│   └── adr/
│       ├── ADR-001.md    # why function-calling with the GenAI SDK was chosen over LangChain
│       ├── ADR-002.md    # why pytest subprocess over importlib
│       └── ADR-003.md    # why Render over Railway
├── .env.example
├── requirements.txt
└── README.md
```

---