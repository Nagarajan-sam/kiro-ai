"""Application factory for the Student Management app.

Call ``create_app()`` to build and configure a Flask application. Using a
factory makes it easy for tests to create an isolated app with its own
temporary database.
"""

import os

from flask import Flask


def create_app(test_config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__, instance_relative_config=True)

    # Default configuration.
    app.config.from_mapping(
        SECRET_KEY="dev",  # Change this in production.
        DATABASE=os.path.join(app.instance_path, "students.sqlite"),
    )

    if test_config is not None:
        # Tests pass their own config (e.g. a temporary database path).
        app.config.update(test_config)

    # Make sure the instance folder exists (SQLite file lives here).
    os.makedirs(app.instance_path, exist_ok=True)

    # Register database handlers and the `init-db` CLI command.
    from app import db

    db.init_app(app)

    # Register all page and API routes.
    from app import routes

    app.register_blueprint(routes.bp)

    return app
