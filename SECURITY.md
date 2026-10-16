# Security Checklist

Status key: [x] done and tested, [ ] open or deferred.

## Input handling

- [x] Server validates every field. Client checks are UX only.
- [x] Strict field allowlist. Unknown fields rejected (blocks mass assignment).
- [x] Length limits on every input (name 100, email 254, URL 2048, query 80).
- [x] Control characters rejected.
- [x] Internship ID format checked and existence verified.
- [x] Request body capped at 4 KB (413).
- [x] JSON content type required (415). Malformed JSON rejected (400).

## Injection

- [x] All SQL uses `?` placeholders. No string-built queries.
- [x] LIKE wildcards (`%`, `_`) escaped, so search is literal.
- [x] Output escaped in the frontend (`esc()` before `innerHTML`, quotes included).
- [x] Tests cover SQLi, wildcard abuse, and HTML payloads.

## URLs

- [x] Only `https://` accepted. Rejects `javascript:`, `data:`, `ftp:`.
- [x] Rejects embedded credentials and malformed hosts or ports.

## Headers

- [x] Content-Security-Policy: `default-src 'self'`, no inline script or style, `frame-ancestors 'none'`.
- [x] X-Content-Type-Options: nosniff
- [x] X-Frame-Options: DENY
- [x] Referrer-Policy: no-referrer
- [x] Permissions-Policy disables geolocation, microphone, camera.
- [x] Cross-Origin-Opener-Policy and Cross-Origin-Resource-Policy: same-origin
- [x] Strict-Transport-Security (effective only over HTTPS)
- [x] API responses use Cache-Control: no-store

## Rate limiting

- [x] Per-IP limits on both endpoints (Flask-Limiter).
- [x] Rate-limited requests return JSON 429 and are logged.
- [ ] Limits are in memory. They reset on restart and are not shared across processes.
- [x] Behind a reverse proxy, set `TRUST_PROXY=1` (ProxyFix, one hop). Confirm the proxy sends X-Forwarded-For after deploy.

## Logging and monitoring

- [x] Request logs hold method, path, and status only. No bodies or query strings.
- [x] Names and emails are never logged.
- [x] Unhandled errors logged with traceback. Client gets a generic 500.
- [x] Health endpoint at `/api/health` checks the database.

## Data

- [x] Parameterized queries only.
- [x] Duplicate applications blocked by a DB UNIQUE constraint (race-safe).
- [x] Emails normalized to lowercase before storage.
- [x] No secrets in the repo. Config comes from env vars.
- [ ] Applications are stored in plain text. Decide on retention and encryption before real users.
- [ ] No authentication on POST. Anyone can submit. Add CAPTCHA or an API token if spam appears.

## Transport and deployment

- [ ] HTTPS not enforced by the app. The host terminates TLS. Redirect HTTP to HTTPS at the host.
- [ ] Production WSGI server: PythonAnywhere's WSGI. `app.py` uses Flask's dev server, for local use only.
- [x] `DB_PATH` defaults to `data/`, outside the static folder.

## Frontend

- [x] No `eval`, no inline handlers, no third-party scripts.
- [x] `credentials: 'omit'` on fetch.
- [x] Request timeout (10 s) with visible error and retry.
- [x] No `localStorage`. Application state lives on the server.
- [ ] No CSRF token. Mitigated: the API requires `application/json`, which cross-site HTML forms cannot send without a CORS preflight, and no cookies are used. Revisit if auth is added.
