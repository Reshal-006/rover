# Rover Setup Guide

This guide describes how to configure and run Rover on your local machine for development or testing.

## Prerequisites

- **Python 3.11+**: Make sure Python is installed and configured on your path.
- **Git**: Required for cloning repositories.
- **Google Gemini API Key**: Required for code inspection and reasoning. Get your API key from [Google AI Studio](https://aistudio.google.com/).

---

## Installation Steps

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Reshal-006/rover.git
   cd rover
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Copy the environment configuration**:
   ```bash
   cp .env.example .env
   ```

---

## Authentication Configurations

Rover supports two authentication methods: **Personal Access Token (classic)** and **GitHub App**.

### Option A: Personal Access Token (PAT) - Quick Start

Best for testing and local hacking:
1. Go to your GitHub profile → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**.
2. Generate a new token classic with the `repo` scope and `write:discussion` scope.
3. Edit your `.env` file:
   ```env
   USE_GITHUB_APP=false
   GITHUB_TOKEN=ghp_yourClassicTokenHere
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

### Option B: GitHub App Authentication (Recommended)

1. Go to your GitHub settings page → **Developer settings** → **GitHub Apps** → **New GitHub App**.
2. Set configuration values:
   - **Name**: `Rover-YourName`
   - **Homepage URL**: `http://localhost:8501`
   - **Callback URL**: `http://localhost:8000/github/callback`
   - **Webhook**: Enable (Checked)
   - **Webhook URL**: Your public URL (e.g., from Ngrok: `https://xxxx.ngrok-free.app/webhook`)
   - **Webhook secret**: Choose a strong secret string.
3. Grant **Repository permissions**:
   - **Contents**: Read & Write
   - **Issues**: Read & Write
   - **Pull requests**: Read & Write
   - **Metadata**: Read-only
4. Under **Event Subscriptions**, subscribe to:
   - **Issues**
   - **Issue comment**
   - **Pull request**
5. Save and click **Generate a private key** at the bottom of the page. Save the private key PEM file to your project root.
6. Configure your `.env` file:
   ```env
   USE_GITHUB_APP=true
   GITHUB_APP_ID=123456
   GITHUB_PRIVATE_KEY=your_app_private_key.pem
   GITHUB_WEBHOOK_SECRET=your_configured_webhook_secret
   GITHUB_CLIENT_ID=your_app_client_id
   GITHUB_CLIENT_SECRET=your_app_client_secret
   ```

---

## Running Rover Locally

### 1. Launch FastAPI Webhook Listener
```bash
uvicorn api.main:app --reload --port 8000
```
API documentation will be available at `http://localhost:8000/docs`.

### 2. Launch Streamlit Dashboard
```bash
streamlit run dashboard/app.py
```
Open your browser to `http://localhost:8501`.
