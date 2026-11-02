# 🎓 Student Management Web Application

A simple, beginner-friendly web application for managing student records,
built with **Flask** and **SQLite**. It demonstrates a clean, well-commented
full-stack CRUD app with a dashboard, live search, a JSON API, and an
automated pytest test suite.

---

## ✨ Features

| # | Feature | Description |
|---|---------------|---------------------------------------------------|
| 1 | **Add Student** | Create a student with name, email, age, and course. |
| 2 | **View Students** | List all students in a sortable table. |
| 3 | **Edit Student** | Update an existing student's details. |
| 4 | **Delete Student** | Remove a student (with a confirmation prompt). |
| 5 | **Search Student** | Live search by name, email, or course. |
| 6 | **Dashboard** | Summary stats: totals, average age, per-course breakdown, recent students. |

Each student has: `name`, `email` (unique), `age`, `course`, and an
automatic `created_at` timestamp. All input is validated server-side, and
every database query is parameterized to prevent SQL injection.

---

## 🛠️ Technology Stack

- **Backend:** Python 3 + [Flask](https://flask.palletsprojects.com/)
- **Database:** SQLite (via the standard-library `sqlite3`, no ORM)
- **Frontend:** Server-rendered HTML (Jinja2), plain CSS, vanilla JavaScript
- **Testing:** [pytest](https://docs.pytest.org/)

---

## 📁 Project Structure

```
kiro-ai/
├── app/                      # Application package
│   ├── __init__.py           # create_app() application factory
│   ├── db.py                 # SQLite connection + init helpers
│   ├── models.py             # Student data access (CRUD + search + validation)
│   ├── routes.py             # Page routes + JSON API (Blueprint)
│   ├── templates/            # Jinja2 HTML templates
│   │   ├── base.html         # Shared layout (navbar, flashes, footer)
│   │   ├── dashboard.html    # Dashboard page
│   │   ├── students.html     # Student list + search
│   │   └── student_form.html # Add / Edit form
│   └── static/
│       ├── css/style.css     # Styles
│       └── js/main.js        # Live search + AJAX delete
├── tests/                    # pytest test suite
│   ├── conftest.py           # Fixtures (temp DB, test client)
│   ├── test_app.py           # Tests for every feature + API
│   └── _flask_shim/          # Offline test fallback (see note below)
├── schema.sql                # Database schema
├── run.py                    # Local entry point
├── requirements.txt          # Python dependencies
├── .kiro/                    # Kiro steering + agent hooks
│   ├── steering/             # product.md, tech.md, structure.md
│   └── hooks/                # Auto-run tests + verify templates on save
└── README.md
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10 or newer

### 2. Set up a virtual environment (recommended)

```bash
python -m venv .venv
source .venv/bin/activate        # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

```bash
python run.py
```

The first run automatically creates the SQLite database. Then open your
browser at:

```
http://127.0.0.1:5000
```

> You can also (re)create the database manually with the Flask CLI:
> ```bash
> flask --app run init-db
> ```

---

## 🧪 Running the Tests

The project ships with a full pytest suite covering **all six features** plus
validation and the JSON API.

```bash
pytest -v
```

Expected result: **21 passing tests**.

### Note on the offline test fallback

The tests prefer the real Flask. If Flask is not installed (for example in an
offline environment with no access to PyPI), `tests/conftest.py` automatically
falls back to a tiny in-repo compatibility shim in `tests/_flask_shim/` so the
suite can still run. **In any normal setup where `requirements.txt` is
installed, the real Flask is used and the shim is never imported.** The shim is
a test aid only — it is not part of the application and should not be used in
production.

---

## 🌐 JSON API Reference

The web UI is backed by a small JSON API (handy for scripts or a future SPA):

| Method | Endpoint | Description |
|--------|------------------------------|---------------------------------|
| GET    | `/api/students`              | List all students (`?q=` to search) |
| GET    | `/api/students/<id>`         | Get one student |
| POST   | `/api/students`              | Create a student (JSON or form) |
| PUT    | `/api/students/<id>`         | Update a student |
| DELETE | `/api/students/<id>`         | Delete a student |
| GET    | `/api/stats`                 | Dashboard statistics |

Example:

```bash
curl -X POST http://127.0.0.1:5000/api/students \
  -H "Content-Type: application/json" \
  -d '{"name":"Ada Lovelace","email":"ada@example.com","age":28,"course":"CS"}'
```

Validation errors return HTTP `400` with a JSON body like:

```json
{ "errors": { "email": "A student with this email already exists." } }
```

---

## 🤖 Kiro Configuration

This project includes Kiro-specific configuration under `.kiro/`:

### Steering files (`.kiro/steering/`)
Always-included context that guides how code is generated and maintained:
- **`product.md`** – What the app is and its core features.
- **`tech.md`** – Tech stack, conventions, and common commands.
- **`structure.md`** – Project layout and where new code belongs.

### Agent hooks (`.kiro/hooks/`)
Automation that runs on workspace events:
- **`run-tests-on-save`** – Runs the pytest suite automatically whenever a
  Python file in `app/` or `tests/` is saved, surfacing regressions early.
- **`remind-run-after-template-change`** – After a template or static asset is
  saved, reminds you to verify the affected page still renders correctly.

---

## 🔒 Design & Safety Notes

- **SQL injection safe:** every query uses parameterized placeholders.
- **Input validation:** shared `validate_student()` enforces required fields,
  a valid email, a positive age, and unique emails for both the form and API.
- **Isolated tests:** each test runs against its own temporary database.
- **Application factory:** `create_app()` makes configuration and testing easy.

---

## 📄 License

This project is provided as-is for educational purposes.
