import pytest

from app import create_app

VALID = {
    "internship_id": "INT-101",
    "name": "Avadhoot Tople",
    "email": "Keys@Example.com",
    "url": "https://example.com/portfolio",
}


@pytest.fixture
def client(tmp_path):
    app = create_app(db_path=tmp_path / "test.db", rate_limits_enabled=False)
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture
def limited_client(tmp_path):
    app = create_app(db_path=tmp_path / "limited.db", rate_limits_enabled=True)
    return app.test_client()


def post(client, body, **kw):
    return client.post("/api/applications", json=body, **kw)


# Health and static

def test_health_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}


def test_index_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Internship Board" in r.data


def test_unknown_route_returns_json_404(client):
    r = client.get("/api/nope")
    assert r.status_code == 404
    assert "error" in r.get_json()


# Listing and filters

def test_list_returns_all_seed_records(client):
    r = client.get("/api/internships")
    body = r.get_json()
    assert r.status_code == 200
    assert body["count"] == 5
    assert len(body["internships"]) == 5


def test_list_item_shape(client):
    item = client.get("/api/internships").get_json()["internships"][0]
    assert set(item) == {"id", "title", "domain", "mode", "location", "skills", "openings"}
    assert isinstance(item["skills"], list)


def test_filter_by_mode(client):
    body = client.get("/api/internships?mode=Remote").get_json()
    assert body["count"] == 3
    assert all(i["mode"] == "Remote" for i in body["internships"])


def test_filter_by_domain(client):
    body = client.get("/api/internships?domain=UI/UX").get_json()
    assert [i["id"] for i in body["internships"]] == ["INT-103"]


def test_search_matches_skill(client):
    body = client.get("/api/internships?q=sql").get_json()
    assert sorted(i["id"] for i in body["internships"]) == ["INT-102", "INT-104"]


def test_search_wildcards_are_literal(client):
    assert client.get("/api/internships?q=%25").get_json()["count"] == 0  # "%"
    assert client.get("/api/internships?q=_").get_json()["count"] == 0    # "_"


def test_search_sql_injection_is_inert(client):
    r = client.get("/api/internships?q=' OR 1=1 --")
    assert r.status_code == 200
    assert r.get_json()["count"] == 0
    assert client.get("/api/internships").get_json()["count"] == 5


def test_overlong_query_rejected(client):
    r = client.get("/api/internships?q=" + "a" * 81)
    assert r.status_code == 400
    assert "q" in r.get_json()["errors"]


# Applications: success and duplicates

def test_valid_application_created(client):
    r = post(client, VALID)
    assert r.status_code == 201
    assert r.get_json() == {"status": "received"}


def test_duplicate_same_email_same_role_conflicts(client):
    post(client, VALID)
    r = post(client, VALID)
    assert r.status_code == 409


def test_duplicate_check_is_case_insensitive(client):
    post(client, VALID)
    r = post(client, {**VALID, "email": "KEYS@example.com"})
    assert r.status_code == 409


def test_same_email_different_role_allowed(client):
    post(client, VALID)
    r = post(client, {**VALID, "internship_id": "INT-102"})
    assert r.status_code == 201


def test_unknown_internship_404(client):
    r = post(client, {**VALID, "internship_id": "INT-999"})
    assert r.status_code == 404


def test_optional_url_may_be_empty(client):
    r = post(client, {**VALID, "url": ""})
    assert r.status_code == 201


# Applications: validation and security

@pytest.mark.parametrize("field,value", [
    ("email", "not-an-email"),
    ("name", "A"),
    ("name", "Robert'); DROP TABLE applications;--"),
    ("url", "javascript:alert(1)"),
    ("url", "http://example.com"),
    ("url", "https://user:pass@example.com"),
    ("internship_id", "bad-id"),
])
def test_invalid_field_rejected(client, field, value):
    r = post(client, {**VALID, field: value})
    assert r.status_code == 400
    assert field in r.get_json()["errors"]


def test_unknown_field_rejected(client):
    r = post(client, {**VALID, "role": "admin"})
    assert r.status_code == 400
    assert "form" in r.get_json()["errors"]


def test_non_json_content_type_rejected(client):
    r = client.post("/api/applications", data="name=x", content_type="text/plain")
    assert r.status_code == 415


def test_malformed_json_rejected(client):
    r = client.post("/api/applications", data="{bad", content_type="application/json")
    assert r.status_code == 400


def test_body_too_large_rejected(client):
    r = post(client, {**VALID, "name": "A" * 5000})
    assert r.status_code == 413


def test_control_characters_rejected(client):
    r = post(client, {**VALID, "name": "Keys\x00Tople"})
    assert r.status_code == 400


# Security headers and caching

def test_security_headers_on_api(client):
    r = client.get("/api/internships")
    assert "default-src 'self'" in r.headers["Content-Security-Policy"]
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Cache-Control"] == "no-store"
    assert "max-age" in r.headers["Strict-Transport-Security"]


def test_security_headers_on_errors(client):
    r = client.get("/api/nope")
    assert r.headers["X-Frame-Options"] == "DENY"


# Rate limits

def test_application_rate_limit_returns_json_429(limited_client):
    statuses = []
    for i in range(6):
        body = {**VALID, "email": f"user{i}@example.com"}
        statuses.append(post(limited_client, body).status_code)
    assert statuses[:5] == [201] * 5
    assert statuses[5] == 429
    assert "error" in post(limited_client, VALID).get_json()