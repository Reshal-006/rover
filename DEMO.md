# Rover 5-Minute Demo Guide

Showcase Rover's end-to-end repository scanning and autonomous bug-fixing pipeline in under five minutes.

---

## 🎭 Prerequisites
1. Ensure your local server is running:
   - API Backend: `uvicorn api.main:app --reload`
   - Streamlit Dashboard: `streamlit run dashboard/app.py`
2. Prepare a test repository on GitHub (e.g., a fork of `rover-demo-repo` with some security issues like hardcoded credentials or division by zero).
3. Ensure the GitHub App is installed on your test repository.

---

## ⏱️ Step-by-Step Walkthrough

### Step 1: The Repository Scan (1 Minute)
1. Open the Streamlit Dashboard at `http://localhost:8501`.
2. In the **Scan Repository** tab, paste the URL of your test repository.
3. Click **Start Scan**.
4. Observe the live glassmorphic progress bar update through the stages:
   `Cloning` ➔ `Traversal` ➔ `Static Analysis` ➔ `LLM Analysis` ➔ `Ranking`.

### Step 2: Review Findings (1 Minute)
1. Scroll down to see the discovered issues.
2. Select an issue to inspect its details (e.g., a *Potential Hardcoded Secret* or *Division by zero*).
3. Review the severity badge (Critical, High, Medium, Low) and the location details.

### Step 3: Trigger the Fix (1 Minute)
1. On the selected issue card, click **Fix Bug**.
2. This creates a GitHub Issue in your repository and starts the background fixing task.
3. Switch to the **Fix Logs / Runs** tab in the dashboard.
4. Watch the terminal logs or UI output showing:
   - Codebase indexing.
   - Smart local symbol context gathering.
   - A single LLM structured generation call.
   - Local pytest validation.

### Step 4: Verify the Pull Request (2 Minutes)
1. Go to your repository on GitHub.
2. Open the **Pull Requests** tab.
3. Review the newly opened PR:
   - Check the unique branch name: `rover/fix-issue-X-YYYYMMDD-HHMMSS-uuid`.
   - Inspect the PR body description, which details the diagnosis and changes.
   - Review the modified source code patch and the written reproducer unit test.
