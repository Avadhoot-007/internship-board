"""Server-side validation. Client checks are UX only; this layer is authoritative."""
import re
import unicodedata
from urllib.parse import urlsplit

NAME_MIN, NAME_MAX = 2, 100
EMAIL_MAX = 254
URL_MAX = 2048
QUERY_MAX = 80
FILTER_MAX = 60

EMAIL_RE = re.compile(r"[a-z0-9._%+\-]+@[a-z0-9\-]+(?:\.[a-z0-9\-]+)*\.[a-z]{2,}")
INTERNSHIP_ID_RE = re.compile(r"INT-[0-9]{3}")
APPLY_FIELDS = frozenset({"internship_id", "name", "email", "url"})
NAME_EXTRA_CHARS = " .'-"


class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("validation failed")
        self.errors = errors


def _has_control_chars(value):
    return any(unicodedata.category(c) == "Cc" for c in value)


def _clean_text(value, field, errors, max_len):
    """Return stripped text, or None and record an error."""
    if not isinstance(value, str):
        errors[field] = "Must be text."
        return None
    value = value.strip()
    if _has_control_chars(value):
        errors[field] = "Contains invalid characters."
        return None
    if len(value) > max_len:
        errors[field] = f"Must be {max_len} characters or fewer."
        return None
    return value


def _valid_https_url(value):
    if any(c.isspace() for c in value):
        return False
    try:
        parts = urlsplit(value)
        parts.port  # raises ValueError on a malformed port
    except ValueError:
        return False
    return (
        parts.scheme == "https"
        and bool(parts.hostname)
        and parts.username is None
        and parts.password is None
    )


def validate_application(payload):
    """Validate a POST /api/applications body. Returns cleaned values."""
    if not isinstance(payload, dict):
        raise ValidationError({"form": "Send a JSON object."})

    errors = {}
    if set(payload) - APPLY_FIELDS:
        errors["form"] = "Unexpected field(s) in request."

    internship_id = payload.get("internship_id")
    if not isinstance(internship_id, str) or not INTERNSHIP_ID_RE.fullmatch(internship_id):
        errors["internship_id"] = "Invalid internship."

    name = _clean_text(payload.get("name", ""), "name", errors, NAME_MAX)
    if name is not None and "name" not in errors:
        if not (NAME_MIN <= len(name) <= NAME_MAX) or not all(
            c.isalpha() or c in NAME_EXTRA_CHARS for c in name
        ):
            errors["name"] = "Use 2 to 100 letters, spaces, dots, apostrophes or hyphens."

    email = _clean_text(payload.get("email", ""), "email", errors, EMAIL_MAX)
    if email is not None and "email" not in errors:
        email = email.lower()
        if not EMAIL_RE.fullmatch(email):
            errors["email"] = "Enter a valid email, like name@example.com."

    url = None
    raw_url = _clean_text(payload.get("url", ""), "url", errors, URL_MAX)
    if raw_url:
        if _valid_https_url(raw_url):
            url = raw_url
        else:
            errors["url"] = "Enter a full https:// link, or leave this empty."

    if errors:
        raise ValidationError(errors)
    return {"internship_id": internship_id, "name": name, "email": email, "url": url}


def validate_filters(args):
    """Validate GET /api/internships query parameters."""
    errors = {}
    q = _clean_text(args.get("q", ""), "q", errors, QUERY_MAX)
    domain = _clean_text(args.get("domain", ""), "domain", errors, FILTER_MAX)
    mode = _clean_text(args.get("mode", ""), "mode", errors, FILTER_MAX)
    if errors:
        raise ValidationError(errors)
    return {"q": q.lower(), "domain": domain, "mode": mode}
