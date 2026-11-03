"""Data-access layer for students.

Every function here talks to SQLite through ``get_db()``. All SQL uses
parameterized queries (``?`` placeholders) to prevent SQL injection.
Input validation lives in ``validate_student()`` so both the web form
and the JSON API share the same rules.
"""

from app.db import get_db


class ValidationError(Exception):
    """Raised when student input fails validation.

    The ``errors`` attribute maps each invalid field to a message.
    """

    def __init__(self, errors):
        self.errors = errors
        super().__init__("Validation failed")


def validate_student(data, *, student_id=None):
    """Validate and clean student input.

    Returns a dict of cleaned values, or raises ``ValidationError``.
    ``student_id`` is used so that updating a student does not clash
    with its own email during the uniqueness check.
    """
    errors = {}

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    course = (data.get("course") or "").strip()
    age_raw = data.get("age")

    if not name:
        errors["name"] = "Name is required."

    if not email:
        errors["email"] = "Email is required."
    elif "@" not in email or "." not in email:
        errors["email"] = "Enter a valid email address."

    if not course:
        errors["course"] = "Course is required."

    # Age must be a positive integer.
    age = None
    try:
        age = int(age_raw)
        if age <= 0 or age > 150:
            errors["age"] = "Age must be between 1 and 150."
    except (TypeError, ValueError):
        errors["age"] = "Age must be a whole number."

    # Email must be unique (ignore the student's own current email on edit).
    if email and "email" not in errors:
        existing = _find_by_email(email)
        if existing and existing["id"] != student_id:
            errors["email"] = "A student with this email already exists."

    if errors:
        raise ValidationError(errors)

    return {"name": name, "email": email, "age": age, "course": course}


def _find_by_email(email):
    db = get_db()
    return db.execute(
        "SELECT * FROM students WHERE email = ?", (email,)
    ).fetchone()


def get_all_students():
    """Return every student, newest first."""
    db = get_db()
    return db.execute(
        "SELECT * FROM students ORDER BY created_at DESC, id DESC"
    ).fetchall()


def get_student(student_id):
    """Return a single student by id, or ``None`` if not found."""
    db = get_db()
    return db.execute(
        "SELECT * FROM students WHERE id = ?", (student_id,)
    ).fetchone()


def search_students(query):
    """Return students whose name, email, or course matches ``query``."""
    db = get_db()
    like = f"%{query.strip()}%"
    return db.execute(
        """
        SELECT * FROM students
        WHERE name LIKE ? OR email LIKE ? OR course LIKE ?
        ORDER BY created_at DESC, id DESC
        """,
        (like, like, like),
    ).fetchall()


def create_student(data):
    """Validate and insert a new student. Returns the new student's id."""
    clean = validate_student(data)
    db = get_db()
    cursor = db.execute(
        "INSERT INTO students (name, email, age, course) VALUES (?, ?, ?, ?)",
        (clean["name"], clean["email"], clean["age"], clean["course"]),
    )
    db.commit()
    return cursor.lastrowid


def update_student(student_id, data):
    """Validate and update an existing student. Returns True if a row changed."""
    clean = validate_student(data, student_id=student_id)
    db = get_db()
    cursor = db.execute(
        """
        UPDATE students
        SET name = ?, email = ?, age = ?, course = ?
        WHERE id = ?
        """,
        (clean["name"], clean["email"], clean["age"], clean["course"], student_id),
    )
    db.commit()
    return cursor.rowcount > 0


def delete_student(student_id):
    """Delete a student by id. Returns True if a row was removed."""
    db = get_db()
    cursor = db.execute("DELETE FROM students WHERE id = ?", (student_id,))
    db.commit()
    return cursor.rowcount > 0


def get_dashboard_stats():
    """Return summary numbers for the dashboard."""
    db = get_db()
    total = db.execute("SELECT COUNT(*) AS c FROM students").fetchone()["c"]
    courses = db.execute(
        "SELECT COUNT(DISTINCT course) AS c FROM students"
    ).fetchone()["c"]
    avg_age_row = db.execute("SELECT AVG(age) AS a FROM students").fetchone()
    avg_age = round(avg_age_row["a"], 1) if avg_age_row["a"] is not None else 0

    # Count of students per course (for a simple breakdown list).
    per_course = db.execute(
        """
        SELECT course, COUNT(*) AS count
        FROM students
        GROUP BY course
        ORDER BY count DESC, course ASC
        """
    ).fetchall()

    recent = db.execute(
        "SELECT * FROM students ORDER BY created_at DESC, id DESC LIMIT 5"
    ).fetchall()

    return {
        "total_students": total,
        "total_courses": courses,
        "average_age": avg_age,
        "per_course": per_course,
        "recent_students": recent,
    }
