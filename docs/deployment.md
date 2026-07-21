# Rover Deployment Guide

This guide describes how to deploy the Rover system (both the FastAPI webhook listener and the Streamlit dashboard) to production environments using Render, Streamlit Cloud, and Docker.

---

## 1. Environment Variable Requirements

Ensure the following variables are set in your production environments:

| Variable | Required | Value |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | Yes | Google AI Studio Key |
| `OPENROUTER_API_KEY` | No | OpenRouter API Key for fallbacks |
| `OPENROUTER_MODEL` | No | Fallback model ID (default: `deepseek/deepseek-chat:free`) |
| `USE_GITHUB_APP` | Yes | Set to `true` |
| `GITHUB_APP_ID` | Yes | Your GitHub App ID |
| `GITHUB_PRIVATE_KEY` | Yes | Raw private key PEM file content or reference path |
| `WEBHOOK_SECRET` | Yes | Your webhook secret |
| `DASHBOARD_URL` | Yes | Public Streamlit dashboard URL |
| `ROVER_BOT_NAME` | No | Git author name for auto-commits (default: `Rover Agent`) |
| `ROVER_BOT_EMAIL` | No | Git author email for auto-commits (default: `rover@internal.ai`) |

---

## 2. FastAPI Backend Listener (Render)

The FastAPI webhook listener must run continuously to receive incoming events (issues, issue comments) from GitHub and run background fixing agents.

### Steps:
1. Create a new **Web Service** on [Render](https://render.com/) and connect your Rover repository fork.
2. Configure settings:
   - **Runtime**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
3. Add your environment variables in Render's **Environment** tab. For `GITHUB_PRIVATE_KEY`, paste the complete multiline PEM content (including `-----BEGIN RSA PRIVATE KEY-----` headers) directly.
4. Deploy and copy the public HTTPS URL (e.g., `https://rover-api.onrender.com`).
5. Update your GitHub App's **Webhook URL** settings to point to:
   `https://rover-api.onrender.com/webhook`

---

## 3. Streamlit Dashboard (Streamlit Share)

The user dashboard can be hosted for free on Streamlit Community Cloud.

### Steps:
1. Log in to [Streamlit Share](https://share.streamlit.io/).
2. Create a new app and choose:
   - **Repository**: `your-username/rover`
   - **Branch**: `main`
   - **Main file path**: `dashboard/app.py`
3. In **Advanced Settings**, paste the configuration variables into the Secrets text field:
   ```toml
   USE_GITHUB_APP = "true"
   GITHUB_APP_ID = "123456"
   GITHUB_PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
   MIIEpAIBAAKCAQEA0y...
   -----END RSA PRIVATE KEY-----"""
   WEBHOOK_SECRET = "your_secret"
   GEMINI_API_KEY = "your_gemini_key"
   OPENROUTER_API_KEY = "your_openrouter_key"
   DASHBOARD_URL = "https://your-app.streamlit.app"
   ```
4. Click **Deploy**.

---

## 4. Docker Deployment (Single Container)

You can run Rover's FastAPI and Streamlit dashboard together in a single container or separately. Below is a production-ready `Dockerfile` configuration:

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose FastAPI and Streamlit ports
EXPOSE 8000
EXPOSE 8501

# Entry point scripts
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port 8000 & streamlit run dashboard/app.py --server.port 8501 --server.address 0.0.0.0"]
```

### Build and Run Command
```bash
docker build -t rover:v1.0.0 .

docker run -d \
  -p 8000:8000 \
  -p 8501:8501 \
  --env-file .env \
  --name rover-service \
  rover:v1.0.0
```
