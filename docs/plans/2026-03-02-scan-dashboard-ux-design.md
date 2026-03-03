# Scan Dashboard UX Redesign — Design Document

**Date:** 2026-03-02
**Status:** Approved
**Author:** Matt Catsimanes (PM) + Claude (Staff Engineer)

## Problem Statement

The current A11yScope UI is a linear 6-step wizard that supports one scan at a time with no persistence. Users cannot queue scans, view history, resume interrupted work, or manage multiple API keys. All state is lost on server restart.

## Requirements

1. Dashboard-first UI replacing the wizard — scan management is the main view
2. Item-level progress detail showing exactly what's being scanned in real time
3. Multi-scan queue: sequential per API key, parallel across keys
4. Full DB persistence: jobs, progress, results survive restarts and are resumable
5. Multi-key management: save, encrypt, and switch between Canvas API tokens
6. Secure-by-design: CIA triad, no critical/high CWEs, FERPA-aware key handling

## Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| UI paradigm | Dashboard-first | Power users need direct access to scan management |
| Progress detail | Item-level live feed | Users need to see exactly what's being scanned |
| Concurrency | Sequential per key, parallel across keys | Respects Canvas API rate limits (250ms/req) |
| Persistence | Full DB (SQLite/PostgreSQL) | Jobs, progress, results must survive restarts |
| Security | Secure-by-design | University API tokens grant access to FERPA data |

---

## Section 1: Architecture & Data Model

### audit_jobs table

```sql
CREATE TABLE audit_jobs (
    id              TEXT PRIMARY KEY,  -- UUID
    user_id         TEXT NOT NULL REFERENCES users(id),
    api_key_id      TEXT NOT NULL REFERENCES api_keys(id),
    canvas_url      TEXT NOT NULL,
    course_id       INTEGER NOT NULL,
    course_name     TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'queued',
        -- enum: queued, running, complete, failed, cancelled, interrupted
    progress_pct    INTEGER NOT NULL DEFAULT 0,
    current_phase   TEXT,  -- fetching | checking | files | scoring
    current_item    TEXT,  -- sanitized title of item being scanned
    items_total     INTEGER NOT NULL DEFAULT 0,
    items_checked   INTEGER NOT NULL DEFAULT 0,
    issues_found    INTEGER NOT NULL DEFAULT 0,
    result_json     TEXT,  -- full audit result (nullable)
    error_message   TEXT,  -- nullable
    queued_at       TEXT NOT NULL,  -- ISO 8601
    started_at      TEXT,
    completed_at    TEXT,
    checkpoint_json TEXT,  -- resume state
    queue_position  INTEGER NOT NULL DEFAULT 0
);
```

### audit_job_items table

```sql
CREATE TABLE audit_job_items (
    id          TEXT PRIMARY KEY,  -- UUID
    job_id      TEXT NOT NULL REFERENCES audit_jobs(id) ON DELETE CASCADE,
    item_type   TEXT NOT NULL,  -- page, assignment, discussion, quiz, file, etc.
    item_title  TEXT NOT NULL,  -- sanitized, max 200 chars
    status      TEXT NOT NULL DEFAULT 'pending',
        -- enum: pending, checking, done, skipped
    issues      INTEGER NOT NULL DEFAULT 0,
    checked_at  TEXT,
    sort_order  INTEGER NOT NULL
);
```

### api_keys table

```sql
CREATE TABLE api_keys (
    id              TEXT PRIMARY KEY,  -- UUID
    user_id         TEXT NOT NULL REFERENCES users(id),
    name            TEXT NOT NULL,  -- user-friendly label
    canvas_url      TEXT NOT NULL,  -- must be HTTPS
    encrypted_token BLOB NOT NULL,  -- Fernet-encrypted Canvas API token
    token_hint      TEXT NOT NULL,  -- last 4 chars for display
    course_count    INTEGER,  -- cached count from last fetch
    last_used_at    TEXT,
    created_at      TEXT NOT NULL
);
```

### ScanQueueManager

Singleton that manages scan execution:

- On startup: load `queued`/`running` jobs from DB, mark `running` as `interrupted`
- Per API key: maintains an `asyncio.Queue`, one worker coroutine
- Worker loop: pop next job, decrypt key, run scan, update DB, advance queue
- Methods: `enqueue()`, `cancel()`, `resume()`, `get_queue_status()`
- Key material held in memory only during active scan, then dereferenced

---

## Section 2: UI Layout & Views

### Sidebar Navigation

- **Dashboard** — overview of active/queued/recent scans (main view)
- **API Keys** — manage Canvas connections
- **History** — full scan history with search/filter
- **Admin** — existing admin panel (role-gated)

### Dashboard View

Three sections stacked vertically:

1. **Active Scans** — cards showing course name, progress bar, current phase,
   current item name, running issue count. Clickable to open scan detail.
2. **Queue** — ordered list with position numbers, cancel buttons.
   Drag-to-reorder within same API key's queue.
3. **Recently Completed** — table with course, score, issue count, timestamp.
   Clickable to view full results.

Header contains `[+ New Scan]` button.

### Scan Detail View

Opened by clicking an active or completed scan card.

- **Header**: back arrow, course name, overall progress bar
- **Phase stepper**: 4 phases (Fetching -> Checking -> Files -> Scoring) with
  done/active/pending states
- **Current item indicator**: "Now: Assignment 3 - Essay Rubric"
- **Live feed**: scrollable list of all content items with status icons
  (done, active, pending) and issue counts. Auto-scrolls to active item.
- **Running stats bar**: Items checked/total, Issues found, Files checked/total
- **Action buttons**: Cancel Scan (when running), Resume (when interrupted)
- On completion: transitions to results view with score gauge, issues table,
  fix and report buttons (existing functionality)

### New Scan Modal

Triggered by `[+ New Scan]` button. Contains:

- API key dropdown (select saved key or add new inline)
- Course list fetched from Canvas API with search/filter
- Multi-select checkboxes with "Select All"
- Previously scanned courses show badge with last score
- "Start N Scans" button queues selected courses

### API Keys View

List of saved keys showing:
- Name, Canvas URL, course count, last used timestamp
- Edit and Delete buttons
- `[+ Add Key]` button opens inline form
- Tokens displayed as masked (last 4 chars only)

---

## Section 3: WebSocket Protocol

### Message Types

```json
{"type": "phase", "phase": "checking", "label": "Checking content items"}

{"type": "item_start", "item_id": "uuid", "item_type": "assignment",
 "title": "Essay Rubric", "index": 18, "total": 26}

{"type": "item_done", "item_id": "uuid", "issues": 3,
 "index": 18, "total": 26}

{"type": "stats", "items_checked": 18, "items_total": 26,
 "issues_found": 12, "files_checked": 0, "files_total": 8,
 "progress_pct": 68}

{"type": "complete", "score": 87.5, "total_issues": 15}

{"type": "error", "message": "Canvas API rate limited, retrying..."}
```

### Connection Model

- URL: `wss://{host}/ws/scan/{job_id}` (WSS required in production)
- Auth: first message after connect must be `{"type": "auth", "token": "<jwt>"}`
- Server rejects connection if no valid auth within 5 seconds
- On reconnect: server replays completed items from `audit_job_items` table
  so the UI catches up instantly

---

## Section 4: Queue Management API

```
POST   /api/scans              Start/queue scans {key_id, course_ids: [...]}
GET    /api/scans              List scans (filterable: status, key_id)
GET    /api/scans/{id}         Scan detail + items
DELETE /api/scans/{id}         Cancel queued/running scan
POST   /api/scans/{id}/resume  Resume interrupted scan from checkpoint
PATCH  /api/scans/queue        Reorder queue [{id, position}, ...]

POST   /api/keys               Save API key {name, canvas_url, token}
GET    /api/keys               List saved keys (tokens masked)
GET    /api/keys/{id}/courses  Fetch courses for a key
PUT    /api/keys/{id}          Update key name/token
DELETE /api/keys/{id}          Delete key + cascade cancel queued scans
```

Existing `/api/audit` endpoints preserved for backward compatibility.

---

## Section 5: Resume & Checkpoint Logic

### Checkpoint Storage

`checkpoint_json` column stores resume state:

```json
{
  "last_completed_index": 17,
  "phase": "checking",
  "items_fetched": true,
  "fetched_items_snapshot": [...]
}
```

### Resume Flow

1. User clicks "Resume" on interrupted scan
2. `POST /api/scans/{id}/resume`
3. Queue manager picks it up, skips fetch phase if items cached,
   starts checking from `last_completed_index + 1`
4. WebSocket replays completed items, then continues live

### Server Restart Recovery

- On startup: query `status IN ('running', 'queued')`
- `running` jobs set to `interrupted` (user can resume manually)
- `queued` jobs re-enter queue in original `queue_position` order
- No automatic resume of running jobs (avoids duplicate API calls)

---

## Section 6: Security Architecture

### Threat Model

| Threat | Mitigation | CWE |
|--------|-----------|-----|
| API key theft via XSS | HttpOnly cookies, CSP, textContent rendering | CWE-79 |
| API key exposure in logs | Masking middleware, no query param tokens | CWE-532 |
| API key theft from DB | Fernet encryption at rest (HKDF-derived key) | CWE-312 |
| SQL injection | SQLAlchemy ORM parameterized queries, Pydantic validation | CWE-89 |
| CSRF | SameSite=Strict cookies, custom header check | CWE-352 |
| Broken authentication | JWT expiry (15min), refresh rotation, rate limiting | CWE-287 |
| Insecure deserialization | Strict JSON parsing only, no unsafe deserializers | CWE-502 |
| SSRF via Canvas URL | HTTPS-only validation, URL allowlisting option | CWE-918 |
| Token in URL | WebSocket auth via first message, not query param | CWE-598 |
| Dependency vulns | pip-audit in CI, pinned + hashed deps | CWE-1104 |

### API Key Protection

- Encrypted at rest: Fernet symmetric encryption
- Encryption key: HKDF-derived from server SECRET_KEY (key separation)
- Never returned to frontend in plaintext (last 4 chars only)
- Never logged — Authorization headers masked in all logging
- In-memory only during active scan, then dereferenced

### XSS Prevention

- All Canvas-sourced strings sanitized server-side (strip HTML, limit 200 chars)
- Frontend uses Alpine.js `x-text` (auto-escapes) — no innerHTML for dynamic data
- Content-Security-Policy blocks external scripts and inline execution
- Security headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`

### Input Validation

- Canvas URL must be HTTPS (enforced by Pydantic validator)
- Course IDs: integer-only, no duplicates, max 50 per request
- Key names: alphanumeric + spaces/hyphens/dots only, max 100 chars
- Request body size: 1MB max at ASGI layer

### Authentication & Session Security

- JWT in HttpOnly + Secure + SameSite=Strict cookies (not localStorage)
- Refresh tokens: server-side storage with rotation (each use invalidates old)
- CSRF: SameSite=Strict + custom `X-Requested-With` header check
- Rate limiting: 10 scan starts/min/user, 100 API calls/min/user
- Authorization: users can only access their own keys and scans
- Admin can view all scans but cannot decrypt other users' tokens

### WebSocket Security

- WSS (TLS) required in production
- Auth via first message after connect (not URL query param)
- 5-second auth timeout — connection dropped if no valid token
- Job ownership verified: user can only connect to their own scans

### Security Headers (middleware)

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'; script-src 'self';
    style-src 'self' 'unsafe-inline'; connect-src 'self' wss:
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
Cache-Control: no-store (on API responses with sensitive data)
X-XSS-Protection: 0 (legacy filter disabled in favor of CSP)
```

### Audit Trail

All security-relevant events logged:
- Key CRUD operations
- Scan lifecycle events
- Failed authentication attempts (rate-limited to prevent log flooding)
- Admin actions
- Fields: user_id, action, resource_type, resource_id, ip_address, timestamp

### Dependency & Runtime Security

- All deps pinned with hashes in requirements.txt
- pip-audit + bandit in CI pipeline
- No dynamic code execution patterns (no unsafe deserializers, no shell=True)
- Docker runs as non-root user
- Base image: python:3.12-slim (minimal attack surface)
- All serialization uses JSON only — safe, well-understood format

---

## Tech Stack (No New Frameworks)

All changes use existing dependencies:
- **Backend**: FastAPI, SQLAlchemy, Alembic, cryptography (Fernet)
- **Frontend**: Alpine.js, Pico CSS, vanilla JS
- **Infra**: Existing Docker Compose setup

No new frontend frameworks. No React migration. The existing Alpine.js SPA
pattern is sufficient for the dashboard UI.
