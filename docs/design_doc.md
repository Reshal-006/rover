# Rover — Design Document

## Problem Statement

Developers spend 20 to 30 percent of their time debugging simple,
reproducible bugs. These follow a predictable pattern: read the
error, find the file, write a test, fix the code. Rover automates
that pattern using GPT-4o function calling.

## Segment

Segment 3 — Foundations of Applied Machine Learning
Problem: I1 (Custom variant — Autonomous Bug-Fixing AI Agent)

## Data Source

GitHub Issues filed on a target repository. The agent clones the
target repo and reads its source files locally. No external dataset
is used — the codebase IS the data.

## The Three ML Problems Inside Rover

1. Code understanding: reading and searching source files to locate
   the likely root cause of a bug.
2. Test generation: writing a pytest test that reproduces the bug
   and will pass once the fix is applied.
3. Fix generation: producing a minimal, targeted code change that
   resolves the root cause without breaking anything else.

## Architecture (overview)

GitHub Issue → FastAPI webhook → Agent orchestrator (while loop)
→ GPT-4o function calling → 4 tools (read_file, search_code,
edit_file, run_tests) → GitHub comment + Pull Request
→ Streamlit dashboard

## Tech Stack

See README.md tech stack table.

## 5-Week Plan (high level)

Week 1: Environment, folder structure, tool layer basics.
Week 2: GPT-4o function calling loop, GitHub API integration.
Week 3: FastAPI webhook, Streamlit dashboard, confidence score.
Week 4: Deploy to Render and Streamlit Cloud.
Week 5: Final polish, submission, showcase.

## Mini-Extension

Confidence score: before attempting any fix, the agent rates its
own certainty (0-100%) that it found the root cause. If below 50,
it posts a clarifying question on the Issue instead of guessing.

## Known Risks

- GPT-4o API costs money. Need to monitor token usage carefully.
- Agent may fail on bugs requiring changes across multiple files.
- Render free tier has 15-min idle spin-down.