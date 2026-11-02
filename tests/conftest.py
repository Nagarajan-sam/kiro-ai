"""Shared pytest fixtures.

Each test gets a fresh Flask app backed by a temporary SQLite database,
so tests never touch real data and never interfere with each other.
"""

import os
import sys
import tempfile

import pytest

# Prefer the real Flask. Only if it is not installed (e.g. an offline
# sandbox that cannot reach PyPI) do we register the minimal in-repo shim
# under the name "flask" so the test suite can still run. In any normal
# environment this fallback is never used.
try:  # pragma: no cover - environment dependent
    import flask  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - environment dependent
    sys.path.insert(0, os.path.dirname(__file__))
    import _flask_shim

    sys.modules["flask"] = _flask_shim

from app import create_app  # noqa: E402
from app.db import init_db  # noqa: E402


@pytest.fixture
def app():
    """Create an app configured for testing with a temporary database."""
    db_fd, db_path = tempfile.mkstemp(suffix=".sqlite")

    app = create_app(
        {
            "TESTING": True,
            "DATABASE": db_path,
            "SECRET_KEY": "test",
            "WTF_CSRF_ENABLED": False,
        }
    )

    # Create the schema inside this app's context.
    with app.app_context():
        init_db()

    yield app

    # Clean up the temporary database file.
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """A test client for making requests without a running server."""
    return app.test_client()


@pytest.fixture
def sample_student():
    """A valid student payload tests can reuse."""
    return {
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "age": "28",
        "course": "Computer Science",
    }
