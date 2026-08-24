# Backend Endpoints Audit (automatic summary)

Generated: brief audit to identify public vs protected endpoints.

Summary:

- Public endpoints (intentionally unauthenticated):
  - `GET /api/v1/health` — health check
  - `GET /api/v1/auth/github/url` — OAuth start URL
  - `POST /api/v1/auth/github/callback` — OAuth token exchange

- Most other API endpoints in `apps/backend/app/api/v1/endpoints.py` require `Depends(get_current_user)` and are protected by session JWTs. Examples include `/repositories`, `/repositories/sync`, `/scans`, `/fixes/{bug_id}`.

Notes & recommendations:

- I intentionally did not force a global auth dependency at the router level because some endpoints (OAuth/callback, health) must remain public. Instead, review any endpoints that do not use `Depends(get_current_user)` and confirm they should be public.
- For production scaling, use Redis (configured via `REDIS_URL`) for shared rate-limiting and caches — I added Redis-backed rate limiting to `apps/backend/app/main.py` (falls back to in-memory when Redis is unavailable).
- Recommended follow-ups:
  1. Review each endpoint in `apps/backend/app/api/v1/endpoints.py` for unintended public exposure.
 2. Add unit/integration tests asserting protected endpoints return 401 without an Authorization header.
 3. Move sensitive background tasks and long-running jobs behind explicit role checks where appropriate.

If you want, I can (a) make a PR that automatically adds `Depends(get_current_user)` to specific endpoints you identify as missing it, or (b) produce a checklist of endpoints I found that lack auth for your review.
