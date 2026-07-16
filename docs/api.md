# Rover API Reference

The Rover API is powered by FastAPI and listens for webhooks, starts asynchronous scans, and exposes status updates.

## Base URL
When running locally: `http://localhost:8000`

---

## Endpoints

### 1. `POST /webhook`
Handles event delivery from GitHub Apps and GitHub classic webhooks.

- **Request Headers**:
  - `X-Hub-Signature-256`: Signature validation header.
  - `X-GitHub-Event`: Specifies event types (`issues`, `issue_comment`, `ping`).
- **Response**:
  - `200 OK` on successful event consumption.
  - `401 Unauthorized` if webhook signatures do not match.

---

### 2. `POST /scan`
Triggers an asynchronous scan of a repository.

- **Request Body** (JSON):
  ```json
  {
    "repository": "https://github.com/owner/repo"
  }
  ```
- **Response**:
  - `202 Accepted`
  - Body:
    ```json
    {
      "scan_id": "scan-xxxxxx",
      "status": "scanning",
      "repository": "https://github.com/owner/repo"
    }
    ```

---

### 3. `GET /scan/{scan_id}`
Retrieves details and progress metrics of a specific scan.

- **Parameters**:
  - `scan_id` (Path, String)
- **Response**:
  - `200 OK`
  - Body:
    ```json
    {
      "scan_id": "scan-xxxxxx",
      "repository": "https://github.com/owner/repo",
      "status": "completed",
      "phase": "deduplicating",
      "progress": 100,
      "bugs_count": 3
    }
    ```

---

### 4. `GET /health`
Liveness probe check.

- **Response**:
  - `200 OK`
  - Body:
    ```json
    {
      "status": "healthy"
    }
    ```
