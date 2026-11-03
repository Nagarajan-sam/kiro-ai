"""Feature tests for the Student Management app.

These tests exercise every feature end-to-end through the HTTP layer:
Add, View, Edit, Delete, Search, Dashboard, plus validation and the
JSON API.
"""


def _add_student(client, **overrides):
    """Helper: create a student via the API and return the JSON body."""
    data = {
        "name": "Grace Hopper",
        "email": "grace@example.com",
        "age": "35",
        "course": "Mathematics",
    }
    data.update(overrides)
    return client.post("/api/students", json=data)


# --------------------------------------------------------------------------
# Pages render
# --------------------------------------------------------------------------

def test_dashboard_renders(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Dashboard" in resp.data
    assert b"Total Students" in resp.data


def test_students_page_renders_empty(client):
    resp = client.get("/students")
    assert resp.status_code == 200
    assert b"No students found." in resp.data


def test_add_form_renders(client):
    resp = client.get("/students/add")
    assert resp.status_code == 200
    assert b"Add Student" in resp.data


# --------------------------------------------------------------------------
# Feature 1: Add Student
# --------------------------------------------------------------------------

def test_add_student_via_form(client, sample_student):
    resp = client.post("/students/add", data=sample_student, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Student added successfully." in resp.data
    assert b"Ada Lovelace" in resp.data


def test_add_student_via_api(client):
    resp = _add_student(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["name"] == "Grace Hopper"
    assert body["id"] > 0


def test_add_student_validation_errors(client):
    resp = client.post("/api/students", json={"name": "", "email": "bad", "age": "x", "course": ""})
    assert resp.status_code == 400
    errors = resp.get_json()["errors"]
    assert "name" in errors
    assert "email" in errors
    assert "age" in errors
    assert "course" in errors


def test_duplicate_email_rejected(client, sample_student):
    client.post("/api/students", json=sample_student)
    resp = client.post("/api/students", json=sample_student)
    assert resp.status_code == 400
    assert "email" in resp.get_json()["errors"]


# --------------------------------------------------------------------------
# Feature 2: View Students
# --------------------------------------------------------------------------

def test_view_students_list(client, sample_student):
    client.post("/api/students", json=sample_student)
    resp = client.get("/students")
    assert b"Ada Lovelace" in resp.data
    assert b"ada@example.com" in resp.data


def test_api_list_students(client):
    _add_student(client, email="a@example.com")
    _add_student(client, email="b@example.com", name="Alan Turing")
    resp = client.get("/api/students")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 2


# --------------------------------------------------------------------------
# Feature 3: Edit Student
# --------------------------------------------------------------------------

def test_edit_student_via_api(client):
    created = _add_student(client).get_json()
    resp = client.put(
        f"/api/students/{created['id']}",
        json={"name": "Grace M. Hopper", "email": "grace@example.com", "age": "36", "course": "CS"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Grace M. Hopper"
    assert resp.get_json()["age"] == 36


def test_edit_nonexistent_student(client):
    resp = client.put("/api/students/999", json={"name": "X", "email": "x@x.com", "age": "20", "course": "C"})
    assert resp.status_code == 404


def test_edit_form_renders(client):
    created = _add_student(client).get_json()
    resp = client.get(f"/students/{created['id']}/edit")
    assert resp.status_code == 200
    assert b"Grace Hopper" in resp.data


# --------------------------------------------------------------------------
# Feature 4: Delete Student
# --------------------------------------------------------------------------

def test_delete_student_via_api(client):
    created = _add_student(client).get_json()
    resp = client.delete(f"/api/students/{created['id']}")
    assert resp.status_code == 200
    # It should be gone now.
    assert client.get(f"/api/students/{created['id']}").status_code == 404


def test_delete_nonexistent_student(client):
    assert client.delete("/api/students/999").status_code == 404


def test_delete_student_via_form(client):
    created = _add_student(client).get_json()
    resp = client.post(f"/students/{created['id']}/delete", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Student deleted." in resp.data


# --------------------------------------------------------------------------
# Feature 5: Search Student
# --------------------------------------------------------------------------

def test_search_by_name(client):
    _add_student(client, name="Alan Turing", email="alan@example.com", course="Logic")
    _add_student(client, name="Ada Lovelace", email="ada@example.com", course="Math")
    resp = client.get("/api/students?q=Alan")
    results = resp.get_json()
    assert len(results) == 1
    assert results[0]["name"] == "Alan Turing"


def test_search_by_course(client):
    _add_student(client, name="Alan Turing", email="alan@example.com", course="Logic")
    _add_student(client, name="Ada Lovelace", email="ada@example.com", course="Mathematics")
    resp = client.get("/api/students?q=Math")
    results = resp.get_json()
    assert len(results) == 1
    assert results[0]["course"] == "Mathematics"


def test_search_no_match(client):
    _add_student(client)
    resp = client.get("/api/students?q=zzzznotfound")
    assert resp.get_json() == []


def test_search_page_filters(client):
    _add_student(client, name="Alan Turing", email="alan@example.com")
    _add_student(client, name="Ada Lovelace", email="ada@example.com")
    resp = client.get("/students?q=Turing")
    assert b"Alan Turing" in resp.data
    assert b"Ada Lovelace" not in resp.data


# --------------------------------------------------------------------------
# Feature 6: Dashboard stats
# --------------------------------------------------------------------------

def test_dashboard_stats_api(client):
    _add_student(client, name="A", email="a@example.com", age="20", course="Math")
    _add_student(client, name="B", email="b@example.com", age="30", course="Science")
    resp = client.get("/api/stats")
    stats = resp.get_json()
    assert stats["total_students"] == 2
    assert stats["total_courses"] == 2
    assert stats["average_age"] == 25.0
    assert len(stats["recent_students"]) == 2


def test_dashboard_stats_empty(client):
    stats = client.get("/api/stats").get_json()
    assert stats["total_students"] == 0
    assert stats["average_age"] == 0
