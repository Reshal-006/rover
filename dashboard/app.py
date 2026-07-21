"""
dashboard/app.py

DEPRECATION NOTICE:
Streamlit UI has been completely replaced by the React 19 + TypeScript + Vite + Tailwind CSS Enterprise SaaS Application in apps/web.

Please launch the modern frontend via:
    npm run dev:web
or run the backend API via:
    uvicorn apps.backend.app.main:app --reload
"""

import streamlit as st

st.set_page_config(page_title="Rover — Streamlit Migration", page_icon="🚀", layout="centered")

st.title("🚀 Rover Has Upgraded to React 19!")
st.subheader("Streamlit Dashboard Replaced")

st.info("""
Rover has been rebuilt into a commercial-grade, multi-tenant AI Developer SaaS platform.

### How to Launch Rover v2.0:
1. **Frontend App (React 19 SPA)**:
   ```bash
   npm run dev:web
   ```
   Open `http://localhost:3000`

2. **Backend API (FastAPI Enterprise)**:
   ```bash
   uvicorn apps.backend.app.main:app --reload
   ```
   Open API docs at `http://localhost:8000/docs`
""")