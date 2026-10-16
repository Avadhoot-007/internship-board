"""Internship Board API: Flask + SQLite, server-side validation, rate limits, secure headers."""
import json
import os
import sqlite3
from pathlib import Path

from flask import Flask, abort, g, jsonify, request, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix

from validation import ValidationError, validate_application, validate_filters

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATA_FILE = BASE_DIR / "data" / "internships.json"
DEFAULT_DB = BASE_DIR / "applications.db"

SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "connect-src 'self'; form-action 'self'; frame-ancestors 'none'; "
        "base-uri 'none'; object-src 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}

ERROR_MESSAGES = {
    400: "Bad request.",
    404: "Not found.",
    405: "Method not allowed.",
    413: "Request body too large.",
    415: "Content-Type must be application/json.",
    429: "Too many requests. Try again shortly.",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS internships (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    domain      TEXT NOT NULL,
    mode        TEXT NOT NULL,
    location    TEXT NOT NULL,
    skills      TEXT NOT NULL,
    search_text TEXT NOT NULL,
    openings    INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS applications (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    internship_id TEXT NOT NULL REFERENCES internships(id),
    name          TEXT NOT NULL,
    email         TEXT NOT NULL,
    portfolio_url TEXT,
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (internship_id, email)
);
"""

UPSERT_INTERNSHIP = """
INSERT INTO internships (id, title, domain, mode, location, skills, search_text, openings)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
    title = excluded.title, domain = excluded.domain, mode = excluded.mode,
    location = excluded.location, skills = excluded.skills,
    search_text = excluded.search_text, openings = excluded.openings
"""


def _connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path):
    conn = _connect(path)
    try:
        conn.executescript(SCHEMA)
        rows = json.loads(DATA_FILE.read_text(encoding="utf-8"))["internships"]
        conn.executemany(
            UPSERT_INTERNSHIP,
            [
                (
                    r["id"], r["title"], r["domain"], r["mode"], r["location"],
                    json.dumps(r["skills"]),
                    (r["title"] + " " + " ".join(r["skills"])).lower(),
                    r["openings"],
                )
                for r in rows
            ],
        )
        conn.commit()
    finally:
        conn.close()


def _like_escape(value):
    """Make % and _ literal inside a LIKE pattern."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _row_to_internship(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "domain": row["domain"],
        "mode": row["mode"],
        "location": row["location"],
        "skills": json.loads(row["skills"]),
        "openings": row["openings"],
    }


def _error(status, message, **extra):
    return jsonify({"error": message, **extra}), status


def create_app(db_path=None, rate_limits_enabled=True):
    app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")
    app.config["MAX_CONTENT_LENGTH"] = 4096
    if os.environ.get("TRUST_PROXY") == "1":
        # Behind one trusted reverse proxy (e.g. PythonAnywhere): read the real client IP.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
    app.config["DB_PATH"] = str(db_path or os.environ.get("DB_PATH", DEFAULT_DB))
    init_db(app.config["DB_PATH"])

    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=[],
        storage_uri="memory://",
        enabled=rate_limits_enabled,
    )
    # Flask-Limiter holds only weak refs to limiter instances; keep a strong ref here.
    app.extensions["limiter"] = limiter

    def get_db():
        if "db" not in g:
            g.db = _connect(app.config["DB_PATH"])
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.after_request
    def add_security_headers(resp):
        for name, value in SECURITY_HEADERS.items():
            resp.headers.setdefault(name, value)
        if request.path.startswith("/api/"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.errorhandler(ValidationError)
    def handle_validation(exc):
        return _error(400, "Validation failed.", errors=exc.errors)

    for code, message in ERROR_MESSAGES.items():
        app.register_error_handler(code, lambda e, m=message, c=code: _error(c, m))

    @app.errorhandler(500)
    def handle_server_error(_exc):
        return _error(500, "Server error. Try again later.")

    @app.get("/")
    def index():
        return send_from_directory(STATIC_DIR, "index.html")

    @app.get("/api/internships")
    @limiter.limit("60 per minute")
    def list_internships():
        f = validate_filters(request.args)
        rows = get_db().execute(
            """
            SELECT id, title, domain, mode, location, skills, openings
            FROM internships
            WHERE (? = '' OR search_text LIKE ? ESCAPE '\\')
              AND (? = '' OR domain = ?)
              AND (? = '' OR mode = ?)
            ORDER BY id
            """,
            (
                f["q"], f"%{_like_escape(f['q'])}%",
                f["domain"], f["domain"],
                f["mode"], f["mode"],
            ),
        ).fetchall()
        items = [_row_to_internship(r) for r in rows]
        return jsonify({"internships": items, "count": len(items)})

    @app.post("/api/applications")
    @limiter.limit("5 per minute")
    @limiter.limit("20 per hour")
    def create_application():
        if not request.is_json:
            abort(415)
        payload = request.get_json(silent=True)
        if payload is None:
            return _error(400, "Malformed JSON.")

        data = validate_application(payload)
        db = get_db()
        exists = db.execute(
            "SELECT 1 FROM internships WHERE id = ?", (data["internship_id"],)
        ).fetchone()
        if exists is None:
            return _error(404, "Unknown internship.")

        try:
            db.execute(
                "INSERT INTO applications (internship_id, name, email, portfolio_url) "
                "VALUES (?, ?, ?, ?)",
                (data["internship_id"], data["name"], data["email"], data["url"]),
            )
            db.commit()
        except sqlite3.IntegrityError:
            return _error(409, "You already applied to this role with that email.")
        return jsonify({"status": "received"}), 201

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=False)
