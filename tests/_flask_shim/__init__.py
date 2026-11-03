"""Minimal Flask-compatible shim — SANDBOX TEST FALLBACK ONLY.

This package exists only so the test suite can run in an offline sandbox
where Flask cannot be installed from PyPI. It implements the small subset
of the Flask / Werkzeug / Jinja2 / click APIs that this project uses.

It is NOT a replacement for Flask. In any normal environment,
``requirements.txt`` installs the real Flask and this shim is never
imported (see ``tests/conftest.py``, which prefers real Flask).

Implemented surface:
  Flask, Blueprint, render_template, request, redirect, url_for, flash,
  get_flashed_messages, jsonify, g, current_app, app_context, test_client,
  open_resource, teardown_appcontext, cli.add_command, and a tiny Jinja-like
  template renderer sufficient for this project's templates.
"""

from ._app import (
    Blueprint,
    Flask,
    current_app,
    flash,
    g,
    get_flashed_messages,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

__all__ = [
    "Flask",
    "Blueprint",
    "render_template",
    "request",
    "redirect",
    "url_for",
    "flash",
    "get_flashed_messages",
    "jsonify",
    "g",
    "current_app",
]
