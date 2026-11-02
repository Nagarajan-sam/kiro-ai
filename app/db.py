"""Database helpers for the Student Management app.

This module manages a single SQLite connection per request using Flask's
application context. Keeping all connection logic here means the rest of
the code never has to worry about opening or closing the database.
"""

import sqlite3

import click
from flask import current_app, g


def get_db():
    """Return the SQLite connection for the current request.

    The connection is created the first time it is needed and reused for
    the rest of the request. Rows are returned as ``sqlite3.Row`` objects
    so we can access columns by name (e.g. ``row["name"]``).
    """
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
        # Enforce foreign keys and UNIQUE constraints.
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(exception=None):
    """Close the database connection at the end of the request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create the database tables from ``schema.sql``."""
    db = get_db()
    with current_app.open_resource("../schema.sql") as f:
        db.executescript(f.read().decode("utf-8"))


@click.command("init-db")
def init_db_command():
    """CLI command: ``flask init-db`` recreates the database."""
    init_db()
    click.echo("Initialized the database.")


def init_app(app):
    """Register database functions with the Flask app."""
    # Close the connection automatically when a request/app context ends.
    app.teardown_appcontext(close_db)
    # Make `flask init-db` available on the command line.
    app.cli.add_command(init_db_command)
