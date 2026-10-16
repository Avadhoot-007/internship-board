# Test Report

**Run:** `python3 -m pytest -v` (Python 3.12, Flask 3.x, Flask-Limiter 4.x, pytest 8)
**Result:** 32 passed, 0 failed

## Coverage by objective

| Objective                                                             | Tests | Result |
| --------------------------------------------------------------------- | ----- | ------ |
| Health check                                                          | 1     | Pass   |
| Static page and JSON 404                                              | 2     | Pass   |
| Listing, filters, search                                              | 9     | Pass   |
| Literal search, SQL injection inert                                   | 3     | Pass   |
| Application create and duplicates                                     | 5     | Pass   |
| Field validation (parametrized)                                       | 7     | Pass   |
| Unknown field, content type, malformed JSON, body size, control chars | 5     | Pass   |
| Security headers and caching                                          | 2     | Pass   |
| Rate limits (5/min, JSON 429)                                         | 1     | Pass   |

## Not yet done

- **Browser UI.** Not run in a headless browser. Check loading, error, retry, and form states by hand.
- **Responsive widths.** Check 360, 768, and desktop.
- **Accessibility audit.** Run axe or Lighthouse on the deployed page.
- **Performance.** Run Lighthouse (mobile) on the deployed page.
- **Production server.** PythonAnywhere WSGI only. Not load tested.
