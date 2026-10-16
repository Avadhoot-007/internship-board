# Internship Board

A responsive internship portal. Flask + SQLite API with a vanilla JS frontend. One app, one URL.

**Live demo:** _add your PythonAnywhere URL here_
**Screenshots:** `docs/` (360px, 768px, desktop)

## Features

- Search by title or skill, filter by domain and work mode
- Application form with server-side validation (authoritative) and client-side hints
- Duplicate protection enforced by a database constraint
- Rate limits on the list and submit endpoints
- Security headers, CSP, and parameterized SQL throughout
- Request logging (method, path, status only) and a health check

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 app.py                # http://127.0.0.1:5000
```

Test the failure state: `http://127.0.0.1:5000/?fail=1`.

## Run tests

```bash
python3 -m pytest -v
```

## API

| Method | Path                                | Purpose                                | Limit                    |
| ------ | ----------------------------------- | -------------------------------------- | ------------------------ |
| GET    | `/`                                 | Frontend                               | none                     |
| GET    | `/api/health`                       | Health check (`200` ok, `503` DB down) | none                     |
| GET    | `/api/internships?q=&domain=&mode=` | List and filter                        | 60/min per IP            |
| POST   | `/api/applications`                 | Submit application (JSON)              | 5/min and 20/hour per IP |

Application body: `{"internship_id","name","email","url"}`. `url` is optional and must be `https://`.

| Status | Meaning                                            |
| ------ | -------------------------------------------------- |
| 201    | Application received                               |
| 400    | Validation failed (`errors` maps field to message) |
| 404    | Unknown internship                                 |
| 409    | Duplicate application (same role and email)        |
| 413    | Body over 4 KB                                     |
| 415    | Content type is not JSON                           |
| 429    | Rate limit reached                                 |

## Configuration

| Env var       | Default                | Purpose                                              |
| ------------- | ---------------------- | ---------------------------------------------------- |
| `DB_PATH`     | `data/applications.db` | SQLite file. Directory is created if missing.        |
| `PORT`        | `5000`                 | Local server port                                    |
| `TRUST_PROXY` | unset                  | Set to `1` behind one reverse proxy (PythonAnywhere) |

## Layout

```
internship-board/
├── app.py                  routes, DB access, headers, logging, rate limits
├── validation.py           server-side validation (authoritative)
├── wsgi.py                 PythonAnywhere entry point
├── requirements.txt
├── data/
│   └── internships.json    seed data (5 roles)
├── static/
│   ├── index.html          page shell
│   ├── app.js              UI logic (fetches the API)
│   └── styles.css          responsive layout, light and dark themes
├── tests/
│   └── test_api.py         integration and security tests
├── SECURITY.md             security checklist
├── TEST_REPORT.md          last test run
└── DEPLOY_PYTHONANYWHERE.md
```

## Engineering decisions

- **One app, not two.** Flask serves the page and the API from one origin. No CORS. The CSP stays `connect-src 'self'`.
- **Server is authoritative.** Client checks only give quick feedback. Every rule is re-checked on the server.
- **SQLite.** One local file. No paid database. Fits the free tier.
- **Parameterized SQL and escaped LIKE wildcards.** Search is literal. Injection payloads are stored as text or rejected.
- **Duplicate check in the database.** A `UNIQUE` constraint is race-safe. Emails are lowercased before storage.
- **Logs hold no PII.** Names and emails are never logged. Only outcomes and internship IDs.

## Known limitations

- Rate limits are in memory. They reset on restart and are per process.
- Applications are stored in plain text. No authentication on submit.
- The free PythonAnywhere web app must be extended monthly.
- Flask's dev server is for local use. Hosting uses PythonAnywhere's WSGI server.
