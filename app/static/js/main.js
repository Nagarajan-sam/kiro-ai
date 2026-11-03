/* ---------------------------------------------------------------------------
   Front-end behaviour for the Student Management app.

   Two enhancements, both progressive (the app still works without JS):
     1. Live search  – filters the table via the JSON API as you type.
     2. Delete button – removes a student via the API without a full reload.
--------------------------------------------------------------------------- */

document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("search-input");
    const tbody = document.getElementById("student-tbody");
    const emptyMessage = document.getElementById("empty-message");
    const searchCount = document.getElementById("search-count");

    // ---- Helpers ---------------------------------------------------------

    function escapeHtml(value) {
        const div = document.createElement("div");
        div.textContent = value == null ? "" : String(value);
        return div.innerHTML;
    }

    function rowHtml(student) {
        return `
            <tr data-id="${student.id}">
                <td>${escapeHtml(student.name)}</td>
                <td>${escapeHtml(student.email)}</td>
                <td>${escapeHtml(student.age)}</td>
                <td>${escapeHtml(student.course)}</td>
                <td class="actions-col">
                    <a class="btn-sm" href="/students/${student.id}/edit">Edit</a>
                    <button class="btn-sm btn-danger" data-delete="${student.id}" data-name="${escapeHtml(student.name)}">Delete</button>
                </td>
            </tr>`;
    }

    function renderStudents(students) {
        if (!tbody) return;
        tbody.innerHTML = students.map(rowHtml).join("");
        if (emptyMessage) emptyMessage.hidden = students.length > 0;
        if (searchCount) {
            searchCount.textContent = students.length
                ? `${students.length} result(s)`
                : "";
        }
    }

    // ---- Live search -----------------------------------------------------

    let debounceTimer = null;
    if (searchInput) {
        searchInput.addEventListener("input", function () {
            clearTimeout(debounceTimer);
            const query = searchInput.value.trim();
            debounceTimer = setTimeout(function () {
                fetch(`/api/students?q=${encodeURIComponent(query)}`)
                    .then((res) => res.json())
                    .then(renderStudents)
                    .catch((err) => console.error("Search failed:", err));
            }, 200);
        });
    }

    // ---- Delete (event delegation) --------------------------------------

    if (tbody) {
        tbody.addEventListener("click", function (event) {
            const button = event.target.closest("[data-delete]");
            if (!button) return;

            const id = button.getAttribute("data-delete");
            const name = button.getAttribute("data-name") || "this student";
            if (!window.confirm(`Delete ${name}?`)) return;

            fetch(`/api/students/${id}`, { method: "DELETE" })
                .then((res) => {
                    if (!res.ok) throw new Error("Delete failed");
                    const row = tbody.querySelector(`tr[data-id="${id}"]`);
                    if (row) row.remove();
                    if (emptyMessage && tbody.children.length === 0) {
                        emptyMessage.hidden = false;
                    }
                })
                .catch((err) => console.error(err));
        });
    }
});
