import json
import sqlite3

import pytest

from app import create_app

VALID = {
    "internship_id": "INT-101",
    "name": "Keys Tester",
    "email": "keys@example.com",
    "url": "https://example.com/portfolio",
}
SEEDED_IDS = ["INT-101", "INT-102", "INT-103", "INT-104", "INT-105"]


@pytest.fixture
def app(tmp_path):
    return create_app(db_path=tmp_path / "test.db", rate_limits_enabled=False)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def limited_client(tmp_path):
    return create_app(db_path=tmp_path / "limited.db", rate_limits_enabled=True).test_client()


def post_app(client, payload, content_type="application/json"):
    body = json.dumps(payload) if isinstance(payload, (dict, list)) else payload
    return client.post("/api/applications", data=body, content_type=content_type)


def list_ids(client, query=""):
    r = client.get("/api/internships" + query)
    assert r.status_code == 200
    return [i["id"] for i in r.get_json()["internships"]]


# ---------- 1. Listing: data integrity and filters ----------

def test_list_returns_all_seeded_internships(client):
    assert list_ids(client) == SEEDED_IDS


def test_list_items_have_expected_shape(client):
    item = client.get("/api/internships").get_json()["internships"][0]
    assert item == {
        "id": "INT-101", "title": "Frontend Intern", "domain": "Full Stack Development",
        "mode": "Remote", "location": "India", "skills": ["HTML", "CSS", "JavaScript"],
        "openings": 3,
    }


def test_filter_by_domain(client):
    assert list_ids(client, "?domain=Full+Stack+Development") == ["INT-101", "INT-102"]


def test_filter_by_mode(client):
    assert list_ids(client, "?mode=Remote") == ["INT-101", "INT-103", "INT-105"]


def test_search_matches_skill_case_insensitively(client):
    assert list_ids(client, "?q=sql") == ["INT-102", "INT-104"]


def test_search_percent_is_literal_not_wildcard(client):
    assert list_ids(client, "?q=%25") == []


def test_search_underscore_is_literal_not_wildcard(client):
    assert list_ids(client, "?q=_") == []


def test_sql_injection_string_returns_nothing_and_table_survives(client):
    assert list_ids(client, "?q=%27+OR+%271%27%3D%271") == []
    assert list_ids(client) == SEEDED_IDS


def test_overlong_query_rejected(client):
    r = client.get("/api/internships?q=" + "a" * 81)
    assert r.status_code == 400
    assert "q" in r.get_json()["errors"]


def test_control_character_in_query_rejected(client):
    r = client.get("/api/internships?q=abc%00")
    assert r.status_code == 400


# ---------- 2. Application form: server-side validation and storage ----------

def test_valid_application_created(client):
    r = post_app(client, VALID)
    assert r.status_code == 201
    assert r.get_json() == {"status": "received"}


def test_email_stored_lowercased(app, client):
    post_app(client, {**VALID, "email": "Keys@Example.COM"})
    conn = sqlite3.connect(app.config["DB_PATH"])
    stored = conn.execute("SELECT email FROM applications").fetchone()[0]
    conn.close()
    assert stored == "keys@example.com"


def test_duplicate_same_role_same_email_rejected_case_insensitive(client):
    assert post_app(client, VALID).status_code == 201
    r = post_app(client, {**VALID, "email": "KEYS@example.com"})
    assert r.status_code == 409


def test_same_email_different_role_allowed(client):
    assert post_app(client, VALID).status_code == 201
    assert post_app(client, {**VALID, "internship_id": "INT-102"}).status_code == 201


def test_unknown_internship_returns_404(client):
    # Format is valid, but the id is not in the database.
    r = post_app(client, {**VALID, "internship_id": "INT-999"})
    assert r.status_code == 404


@pytest.mark.parametrize("bad_id", ["INT-1", "int-101", "INT-101; DROP TABLE x", 101, None])
def test_malformed_internship_id_rejected(client, bad_id):
    r = post_app(client, {**VALID, "internship_id": bad_id})
    assert r.status_code == 400
    assert "internship_id" in r.get_json()["errors"]


@pytest.mark.parametrize("name", ["", " ", "K", "<script>alert(1)</script>", "Keys; DROP TABLE applications",
                                  "A" * 101, "Name123"])
def test_invalid_names_rejected(client, name):
    r = post_app(client, {**VALID, "name": name})
    assert r.status_code == 400
    assert "name" in r.get_json()["errors"]


def test_apostrophe_and_hyphen_names_accepted(client):
    assert post_app(client, {**VALID, "name": "Aoife O'Brien-Smith"}).status_code == 201


@pytest.mark.parametrize("email", ["not-an-email", "a@b", "a b@example.com", "x@example.c",
                                   "<a>@example.com", "a" * 250 + "@example.com"])
def test_invalid_emails_rejected(client, email):
    r = post_app(client, {**VALID, "email": email})
    assert r.status_code == 400
    assert "email" in r.get_json()["errors"]


@pytest.mark.parametrize("url", [
    "http://example.com",
    "javascript:alert(1)",
    "ftp://example.com",
    "https://user:pass@example.com",
    "https://",
    "https://exa mple.com",
    "https://example.com:notaport",
    "data:text/html,<script>alert(1)</script>",
])
def test_unsafe_or_malformed_urls_rejected(client, url):
    r = post_app(client, {**VALID, "url": url})
    assert r.status_code == 400
    assert "url" in r.get_json()["errors"]


def test_empty_url_accepted_and_stored_as_null(app, client):
    assert post_app(client, {**VALID, "url": ""}).status_code == 201
    conn = sqlite3.connect(app.config["DB_PATH"])
    stored = conn.execute("SELECT portfolio_url FROM applications").fetchone()[0]
    conn.close()
    assert stored is None


def test_missing_fields_reported_together(client):
    r = post_app(client, {"internship_id": "INT-101"})
    errors = r.get_json()["errors"]
    assert {"name", "email"} <= set(errors)


def test_unknown_field_rejected_blocks_mass_assignment(client):
    r = post_app(client, {**VALID, "status": "accepted", "id": 7})
    assert r.status_code == 400
    assert "form" in r.get_json()["errors"]


def test_non_json_content_type_rejected(client):
    r = post_app(client, "name=x", content_type="application/x-www-form-urlencoded")
    assert r.status_code == 415


def test_malformed_json_rejected(client):
    r = post_app(client, "{not json", content_type="application/json")
    assert r.status_code == 400


def test_json_array_body_rejected(client):
    r = post_app(client, [VALID])
    assert r.status_code == 400


def test_oversized_body_rejected(client):
    r = post_app(client, {**VALID, "name": "A" * 5000})
    assert r.status_code == 413


def test_sql_injection_in_form_does_not_drop_tables(app, client):
    r = post_app(client, {**VALID, "name": "Robert'); DROP TABLE applications;--"})
    assert r.status_code == 400
    conn = sqlite3.connect(app.config["DB_PATH"])
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert {"applications", "internships"} <= tables


def test_apostrophe_name_is_stored_as_plain_text(app, client):
    post_app(client, {**VALID, "name": "Aoife O'Brien"})
    conn = sqlite3.connect(app.config["DB_PATH"])
    stored = conn.execute("SELECT name FROM applications").fetchone()[0]
    conn.close()
    assert stored == "Aoife O'Brien"


# ---------- 3. Security headers and rate limits ----------

def test_security_headers_present_on_api(client):
    r = client.get("/api/internships")
    assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]
    assert "script-src 'self'" in r.headers["Content-Security-Policy"]
    assert "unsafe-inline" not in r.headers["Content-Security-Policy"]
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Referrer-Policy"] == "no-referrer"
    assert "max-age=" in r.headers["Strict-Transport-Security"]


def test_api_responses_not_cached(client):
    assert client.get("/api/internships").headers["Cache-Control"] == "no-store"


def test_index_served_with_security_headers(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers["X-Frame-Options"] == "DENY"


def test_error_responses_are_json_with_headers(client):
    r = client.get("/api/nope")
    assert r.status_code == 404
    assert r.is_json
    assert r.headers["X-Content-Type-Options"] == "nosniff"


def test_application_endpoint_rate_limited(limited_client):
    statuses = []
    for i in range(6):
        payload = {**VALID, "email": f"user{i}@example.com"}
        statuses.append(post_app(limited_client, payload).status_code)
    assert statuses[:5] == [201] * 5
    assert statuses[5] == 429


def test_rate_limited_response_is_json(limited_client):
    for i in range(5):
        post_app(limited_client, {**VALID, "email": f"u{i}@example.com"})
    r = post_app(limited_client, {**VALID, "email": "last@example.com"})
    assert r.status_code == 429
    assert r.is_json
    assert "error" in r.get_json()


def test_list_endpoint_rate_limited(limited_client):
    codes = [limited_client.get("/api/internships").status_code for _ in range(61)]
    assert codes[:60] == [200] * 60
    assert codes[60] == 429


def test_proxy_header_used_for_rate_limit_key_only_when_trusted(tmp_path, monkeypatch):
    monkeypatch.setenv("TRUST_PROXY", "1")
    client = create_app(db_path=tmp_path / "p.db", rate_limits_enabled=True).test_client()
    # Five requests from client A exhaust its limit; client B must still get through.
    def send(ip, email):
        return client.post("/api/applications", data=json.dumps({**VALID, "email": email}),
                           content_type="application/json", headers={"X-Forwarded-For": ip})
    assert [send("203.0.113.1", f"x{i}@example.com").status_code for i in range(6)][-1] == 429
    assert send("203.0.113.2", "other@example.com").status_code == 201
