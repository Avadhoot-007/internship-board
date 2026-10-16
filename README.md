# Internship Board

Flask + SQLite API with a vanilla JS frontend. Server-side validation, rate limits, and secure headers.

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 app.py            # http://127.0.0.1:5000
```

Test a failure state in the UI: open `http://127.0.0.1:5000/?fail=1`.

## Run tests

```bash
python3 -m pytest -v
```

## API

| Method | Path | Purpose | Limit |
|---|---|---|---|
| GET | `/api/internships?q=&domain=&mode=` | List and filter internships | 60/min per IP |
| POST | `/api/applications` | Submit application (JSON) | 5/min and 20/hour per IP |

POST body: `{"internship_id","name","email","url"}`. `url` is optional and must be `https://`.

Status codes: 201 created, 400 validation, 404 unknown role, 409 duplicate, 413 too large, 415 wrong content type, 429 rate limited.

## Config

| Env var | Default | Purpose |
|---|---|---|
| `DB_PATH` | `applications.db` | SQLite file path |
| `PORT` | `5000` | Server port |

## Layout

- `app.py`: routes, DB access, headers, rate limits
- `validation.py`: server-side validation (authoritative)
- `static/`: frontend
- `data/internships.json`: seed data
- `tests/test_api.py`: integration and security tests
- `SECURITY.md`: security checklist
- `TEST_REPORT.md`: last test run
