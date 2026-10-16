# Test Report

**Run:** `python3 -m pytest -v` (Python 3.12.3, Flask 3.1.3, Flask-Limiter 4.1.1, pytest 8)
**Result:** 59 passed, 0 failed, 0 skipped, 0.8 s
**Lint:** pyflakes clean on `app.py`, `validation.py`, `tests/test_api.py`
**JS check:** `node --check static/app.js` passes (syntax only)

## Coverage by objective

| Objective | Tests | Result |
|---|---|---|
| Load and filter API data | 8 (list shape, domain/mode/search filters, data integrity) | Pass |
| Literal search, no SQLi | 4 (wildcards `%` and `_`, SQLi string, table survival) | Pass |
| Query input validation | 2 (overlong, control chars) | Pass |
| Form validation (server) | 26 parametrized (name, email, URL, internship ID, unknown fields, body type/size) | Pass |
| Application storage | 6 (create, lowercase email, duplicate 409, same email other role, unknown role 404, NULL URL) | Pass |
| SQLi via form | 2 (DROP TABLE payload rejected, apostrophe stored as text) | Pass |
| Security headers | 4 (CSP, nosniff, DENY, HSTS, no-store, headers on errors) | Pass |
| Rate limits | 3 (apply 5/min, list 60/min, JSON 429 body) | Pass |

## Live server smoke test (curl, local run on port 5055)

| Request | Expected | Got |
|---|---|---|
| GET `/api/internships?q=sql` | 200, 2 results, security headers | 200, 2 results, CSP / DENY / HSTS / no-store present |
| POST valid application | 201 | 201 |
| POST same role and email | 409 | 409 |
| POST form-encoded body | 415 | 415 |
| 6 rapid POSTs | 429 after the limit | 201, 201, then 429 (limit reached; earlier requests in the same minute counted) |
| GET `/` and `/app.js` | 200 | 200 |

## Not tested (open)

- **Browser UI.** No headless browser run. Loading, error, retry, and form-state behaviour are checked by reading code only.
- **Responsive widths.** Not run at 360, 768, or desktop widths.
- **Real network failure and timeout.** Not simulated in a browser. Only `?fail=1` was reasoned through.
- **Load and concurrency.** No load test. Rate limits are per process, in memory.
- **Production server and HTTPS.** Flask dev server only. HSTS only matters over HTTPS.
- **Accessibility audit.** Not run.
