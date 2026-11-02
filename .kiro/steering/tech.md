---
inclusion: always
---

# Technology Stack & Conventions

## Stack

- **Backend:** Python 3 + Flask
- **Database:** SQLite (standard-library `sqlite3`, no ORM)
- **Frontend:** Server-rendered HTML (Jinja2), plain CSS, vanilla JavaScript
- **Testing:** pytest

## Conventions

- Use the **application factory** pattern: `create_app()` in `app/__init__.py`.
- Keep database access in `app/db.py` and `app/models.py`.
- Keep all routes in `app/routes.py` using a Flask Blueprint.
- Use **parameterized SQL queries** everywhere (never string formatting) to
  avoid SQL injection.
- Validate and sanitize user input on the server side.
- Return JSON from `/api/*` endpoints; render HTML for page routes.

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the development server
python run.py

# Run the test suite
pytest -v
```

## Environment

- The database path can be overridden with the `DATABASE` config value
  (tests use an isolated temporary database).
