---
inclusion: always
---

# Project Structure

```
kiro-ai/
├── app/                     # Application package
│   ├── __init__.py          # create_app() application factory
│   ├── db.py                # SQLite connection + init helpers
│   ├── models.py            # Student data-access functions (CRUD + search)
│   ├── routes.py            # Page routes + JSON API (Blueprint)
│   ├── templates/           # Jinja2 HTML templates
│   └── static/              # CSS and JavaScript assets
├── tests/                   # pytest test suite
│   ├── conftest.py          # Shared fixtures (temp DB, test client)
│   └── test_app.py          # Feature + API tests
├── schema.sql               # Database schema
├── run.py                   # Local entry point
├── requirements.txt         # Python dependencies
└── README.md                # Documentation
```

## Rules

- New data-access logic goes in `app/models.py`, not in route handlers.
- New routes are registered on the existing Blueprint in `app/routes.py`.
- Each new feature should ship with a corresponding pytest test.
- Templates extend `base.html` for a consistent layout.
