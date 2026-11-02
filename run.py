"""Local entry point for the Student Management app.

Running ``python run.py`` will:
  1. Build the Flask app via the factory.
  2. Create the database tables if the database file does not exist yet.
  3. Start the development server.
"""

import os

from app import create_app
from app.db import init_db

app = create_app()


def _ensure_database():
    """Create tables on first run so the app works out of the box."""
    db_path = app.config["DATABASE"]
    if not os.path.exists(db_path):
        with app.app_context():
            init_db()
        print(f"Created new database at {db_path}")


if __name__ == "__main__":
    _ensure_database()
    app.run(debug=True, host="127.0.0.1", port=5000)
