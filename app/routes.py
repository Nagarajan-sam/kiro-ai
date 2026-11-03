"""Routes for the Student Management app.

Two kinds of endpoints live here:

* **Page routes** (``/``, ``/students`` ...) render HTML templates.
* **API routes** (``/api/students`` ...) accept and return JSON, and are
  used by the front-end JavaScript for live search and deletion.
"""

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from app import models
from app.models import ValidationError

bp = Blueprint("main", __name__)


# --------------------------------------------------------------------------
# Page routes (HTML)
# --------------------------------------------------------------------------

@bp.route("/")
def dashboard():
    """Dashboard with summary statistics."""
    stats = models.get_dashboard_stats()
    return render_template("dashboard.html", stats=stats)


@bp.route("/students")
def list_students():
    """List all students, or filtered results when ``?q=`` is present."""
    query = request.args.get("q", "").strip()
    if query:
        students = models.search_students(query)
    else:
        students = models.get_all_students()
    return render_template("students.html", students=students, query=query)


@bp.route("/students/add", methods=["GET", "POST"])
def add_student():
    """Show the add form (GET) and create a student (POST)."""
    if request.method == "POST":
        try:
            models.create_student(request.form)
            flash("Student added successfully.", "success")
            return redirect(url_for("main.list_students"))
        except ValidationError as err:
            # Re-render the form with errors and the values the user typed.
            return render_template(
                "student_form.html",
                mode="add",
                errors=err.errors,
                student=request.form,
            ), 400
    return render_template("student_form.html", mode="add", student={}, errors={})


@bp.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
def edit_student(student_id):
    """Show the edit form (GET) and update a student (POST)."""
    student = models.get_student(student_id)
    if student is None:
        flash("Student not found.", "error")
        return redirect(url_for("main.list_students"))

    if request.method == "POST":
        try:
            models.update_student(student_id, request.form)
            flash("Student updated successfully.", "success")
            return redirect(url_for("main.list_students"))
        except ValidationError as err:
            return render_template(
                "student_form.html",
                mode="edit",
                errors=err.errors,
                student={**dict(student), **request.form.to_dict()},
            ), 400

    return render_template(
        "student_form.html", mode="edit", student=student, errors={}
    )


@bp.route("/students/<int:student_id>/delete", methods=["POST"])
def delete_student(student_id):
    """Delete a student (used by the non-JS fallback form)."""
    if models.delete_student(student_id):
        flash("Student deleted.", "success")
    else:
        flash("Student not found.", "error")
    return redirect(url_for("main.list_students"))


# --------------------------------------------------------------------------
# JSON API routes
# --------------------------------------------------------------------------

@bp.route("/api/students", methods=["GET"])
def api_list_students():
    """Return all students, or search results when ``?q=`` is given."""
    query = request.args.get("q", "").strip()
    rows = models.search_students(query) if query else models.get_all_students()
    return jsonify([dict(row) for row in rows])


@bp.route("/api/students/<int:student_id>", methods=["GET"])
def api_get_student(student_id):
    student = models.get_student(student_id)
    if student is None:
        return jsonify({"error": "Student not found."}), 404
    return jsonify(dict(student))


@bp.route("/api/students", methods=["POST"])
def api_create_student():
    data = request.get_json(silent=True) or request.form
    try:
        new_id = models.create_student(data)
    except ValidationError as err:
        return jsonify({"errors": err.errors}), 400
    return jsonify(dict(models.get_student(new_id))), 201


@bp.route("/api/students/<int:student_id>", methods=["PUT"])
def api_update_student(student_id):
    if models.get_student(student_id) is None:
        return jsonify({"error": "Student not found."}), 404
    data = request.get_json(silent=True) or request.form
    try:
        models.update_student(student_id, data)
    except ValidationError as err:
        return jsonify({"errors": err.errors}), 400
    return jsonify(dict(models.get_student(student_id)))


@bp.route("/api/students/<int:student_id>", methods=["DELETE"])
def api_delete_student(student_id):
    if models.delete_student(student_id):
        return jsonify({"message": "Student deleted."})
    return jsonify({"error": "Student not found."}), 404


@bp.route("/api/stats", methods=["GET"])
def api_stats():
    stats = models.get_dashboard_stats()
    # Convert Row objects to plain dicts so they are JSON-serializable.
    return jsonify(
        {
            "total_students": stats["total_students"],
            "total_courses": stats["total_courses"],
            "average_age": stats["average_age"],
            "per_course": [dict(r) for r in stats["per_course"]],
            "recent_students": [dict(r) for r in stats["recent_students"]],
        }
    )
