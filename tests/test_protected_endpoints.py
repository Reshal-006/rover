from fastapi.testclient import TestClient
from apps.backend.app.main import app

client = TestClient(app)

PROTECTED_ENDPOINTS = [
    ("GET", "/api/v1/repositories"),
    ("POST", "/api/v1/repositories/sync"),
    ("POST", "/api/v1/scans"),
    ("GET", "/api/v1/scans/scan-1234"),
    ("POST", "/api/v1/fixes/bug-123"),
    ("GET", "/api/v1/dashboard/summary"),
    ("GET", "/api/v1/findings"),
    ("GET", "/api/v1/pull-requests"),
    ("GET", "/api/v1/analytics"),
    ("GET", "/api/v1/history"),
    ("GET", "/api/v1/users/settings"),
    ("PUT", "/api/v1/users/settings"),
    ("DELETE", "/api/v1/history"),
    ("POST", "/api/v1/auth/revoke"),
    ("DELETE", "/api/v1/auth/github"),
    ("DELETE", "/api/v1/workspace"),
]


def _call(method, path):
    if method == "GET":
        return client.get(path)
    if method == "POST":
        # supply minimal JSON for endpoints that expect a body
        if path.startswith("/api/v1/scans"):
            return client.post(path, json={"repository_url": "https://github.com/res/test"})
        if path.startswith("/api/v1/fixes"):
            return client.post(path, json={"repository_url": "https://github.com/res/test", "title": "fix"})
        return client.post(path)
    if method == "PUT":
        return client.put(path, json={})
    if method == "DELETE":
        return client.delete(path)


def test_protected_endpoints_require_auth():
    """Endpoints that are intended to be protected must return 401 without a JWT."""
    for method, path in PROTECTED_ENDPOINTS:
        resp = _call(method, path)
        assert resp.status_code == 401, f"{method} {path} returned {resp.status_code} (expected 401)"


def test_public_endpoints_available():
    # Health should be public
    r = client.get("/api/v1/health")
    assert r.status_code == 200

    # OAuth URL endpoint is public (may return 400 if client id not configured)
    r2 = client.get("/api/v1/auth/github/url")
    assert r2.status_code in (200, 400)

    # OAuth callback without code should return 400
    r3 = client.post("/api/v1/auth/github/callback", json={})
    assert r3.status_code == 400
