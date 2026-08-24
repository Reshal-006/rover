# Public (Unauthenticated) API Endpoints

These endpoints intentionally permit unauthenticated access and are required for OAuth and health checks.

- `GET /api/v1/health` — Health check (public)
- `GET /api/v1/auth/github/url` — Returns GitHub OAuth authorization URL (public)
- `POST /api/v1/auth/github/callback` — OAuth callback / token exchange (public)
- `POST /api/v1/auth/login` — Simulated login helper (public)

All other endpoints in `apps/backend/app/api/v1/endpoints.py` require `Depends(get_current_user)` and are protected by JWT session tokens, or use explicit token validation (e.g., the websocket scan stream expects a `token` query param).

If you want any of the above to require authentication (e.g., restrict OAuth callback usage), tell me which ones and I'll add the dependency.
