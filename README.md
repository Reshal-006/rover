<div align="center">

# Rover 🐕

**Autonomous Codebase Explorer & Auto-Fix Engine**

Rover is an autonomous AI agent designed to proactively scan GitHub repositories for bugs and vulnerabilities, rank findings, and automatically generate fixes, tests, and Pull Requests without human intervention.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Gemini](https://img.shields.io/badge/AI-Gemini%202.5-purple.svg)](https://deepmind.google/technologies/gemini/)

</div>

---

## 📖 Table of Contents
1. [Overview](#-overview)
2. [Motivation](#-motivation)
3. [Architecture](#-architecture)
4. [Features](#-features)
5. [Tech Stack](#-tech-stack)
6. [Installation](#-installation)
7. [Environment Variables](#-environment-variables)
8. [GitHub App Setup](#-github-app-setup)
9. [Running Locally](#-running-locally)
10. [Browser Mini-Extension](#-browser-mini-extension)
11. [Deployment](#-deployment)
12. [Roadmap & Limitations](#-roadmap--limitations)
13. [License](#-license)

---

## 🔍 Overview

Rover operates in two core modes:
1. **Proactive Mode (Scan & Fix)**: Rover clones a repository, performs AST-based security analysis, validates context using Gemini, ranks findings, displays findings in a glassmorphic dashboard, and allows fixing with a single click.
2. **Reactive Mode (Issue-Driven)**: Triggered via GitHub webhook when a user opens an issue on a repository with the label `rover`. Rover reads the issue, writes a failing test reproducing the bug, writes a patch, verifies the test passes, and opens a Pull Request automatically.

---

## 💡 Motivation

Debugging consumes significant engineering hours. Many bugs follow repetitive patterns: read traceback → find file → write regression test → apply a validation patch → push. Rover automates this entire lifecycle, turning manual debugging into a proactive automated review process.

---

## 🏗️ Architecture

```
User repository URL/Issue
       │
       ▼
Webhooks / Trigger API (FastAPI)
       │
       ▼
Asynchronous Scan/Fix Pipelines
       │
       ├─ AST Static Scanner
       ├─ Gemini LLM Reasoning Engine
       └─ Local Git Tools Layer
       │
       ▼
Pull Request + Glassmorphic Streamlit UI
```

Detailed diagrams (including System Architecture, Scan Pipeline, and Fix Pipeline) can be found in the [Architecture Guide](docs/architecture.md).

---

## ✨ Features

- **Proactive Code Scanner**: 9-phase asynchronous pipeline scans codebases for eval injection, hardcoded secrets, and broad try-except blocks.
- **Glassmorphic Dashboard**: Real-time progress monitoring, custom HTML timelines, separate runs & scan histories, and interactive bug cards.
- **One-Click Fixing**: Spawns issue creation and autonomous agent fixing pipelines directly from scan cards.
- **GitHub App Auth**: Seamless token caching, automatic refresh, and multi-repository discovery.
- **Browser Extension**: One-click scanner launcher from your active GitHub repository page.

---

## 🛠️ Tech Stack

| Component | Technology | Why |
|:---|:---|:---|
| **Language Model** | Gemini 2.5 Flash | High context size, cost-efficient, fast tool-calling API. |
| **Backend API** | FastAPI | Asynchronous performance and automatic Swagger docs. |
| **Frontend UI** | Streamlit | Rapid dashboard assembly and responsive glassmorphic themes. |
| **Auth & Client** | PyGithub / GitPython | Full integration with GitHub App tokens and raw Git operations. |
| **Test Runner** | Pytest | Isolated execution with simple return codes. |
| **Extension** | Manifest V3 JS | Secure, light integration with modern browsers. |

---

## 🚀 Installation

Refer to the complete [Setup Guide](docs/setup.md) for local installation instructions. A quick overview is below:

```bash
git clone https://github.com/Reshal-006/rover.git
cd rover
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

---

## ⚙️ Environment Variables

Add the following keys to your `.env` file:
```env
GEMINI_API_KEY=your_gemini_api_key
USE_GITHUB_APP=true
GITHUB_APP_ID=your_app_id
GITHUB_PRIVATE_KEY=your_key.pem
GITHUB_WEBHOOK_SECRET=your_secret
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_client_secret
```

---

## 🤖 GitHub App Setup

1. Create a GitHub App in your settings with **Contents**, **Issues**, and **Pull requests** write permissions.
2. Generate and download a private key PEM file.
3. Configure the webhook to point to your listener API.
4. Read the [Setup Guide](docs/setup.md) for step-by-step configuration.

---

## 💻 Running Locally

1. **Start the API Server**:
   ```bash
   uvicorn api.main:app --reload --port 8000
   ```
2. **Start the Streamlit UI**:
   ```bash
   streamlit run dashboard/app.py
   ```

---

## 🧩 Browser Mini-Extension

We provide a Chrome/Firefox extension that injects a **Scan with Rover** button:
1. Open Chrome/Firefox developer extension settings.
2. Click **Load unpacked** and select the `extension/` folder in the Rover directory.
3. Open any GitHub repository in your active tab, click the extension icon, and launch the scan!

---

## 🌐 Deployment

Read the [Deployment Guide](docs/deployment.md) to learn how to host:
- The FastAPI listener on **Render**
- The Streamlit Dashboard on **Streamlit Cloud**

---

## 🗺️ Roadmap & Limitations

- **Python-Only**: Currently indexes and parses Python files. Support for JavaScript/TypeScript and Go is planned.
- **Subprocess Runner**: Runs tests on the host system. Dockerized sandbox environments are coming next.
- For complete details, see the [Release Notes](docs/release_notes_v1.0.0.md) and [Developer Reflection](docs/reflection.md).

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) - see the LICENSE file for details.