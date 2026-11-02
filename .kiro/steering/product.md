---
inclusion: always
---

# Product Overview

This project is a **Student Management Web Application**.

It lets a school administrator manage student records through a simple,
browser-based interface.

## Core Features

1. **Add Student** – Create a new student record.
2. **View Students** – List all students in a table.
3. **Edit Student** – Update an existing student's details.
4. **Delete Student** – Remove a student record.
5. **Search Student** – Filter students by name, email, or course.
6. **Dashboard** – Show summary statistics (totals and recent activity).

## Student Fields

- `name` – Full name (required)
- `email` – Email address (required, unique)
- `age` – Age in years (required, positive integer)
- `course` – Enrolled course name (required)
- `created_at` – Timestamp set automatically

## Design Goals

- Keep the code **beginner-friendly** and well-commented.
- Prefer clarity over cleverness.
- Keep the app runnable with a single command.
