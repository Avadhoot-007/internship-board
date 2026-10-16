"""PythonAnywhere entry point. Paste this into the WSGI configuration file,
or point the WSGI file at this module. Change USERNAME to your PythonAnywhere user."""
import os
import sys

PROJECT_HOME = "/home/Avadhoot007/internship-board"
if PROJECT_HOME not in sys.path:
    sys.path.insert(0, PROJECT_HOME)

os.environ.setdefault("DB_PATH", os.path.join(PROJECT_HOME, "data", "applications.db"))
os.environ.setdefault("TRUST_PROXY", "1")  # one reverse proxy in front of the app

from app import create_app  # noqa: E402

application = create_app()
