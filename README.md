# CLASSORA — Academic Material & Notice Management System

A Python/Flask + SQLite mini project for teachers to publish academic materials to designated subjects, semesters and sections, and for students to find/download them.

## Features
- Teacher and student accounts with role-based access
- Teacher uploads assigned to subject, semester, section and material category
- Categories: Notes, Exam/Syllabus, Assignment, Project, Practical/Lab, Other
- Targeted notices
- Search and filters
- SQLite persistence, input validation, upload size/type checks
- Demo accounts and sample subjects created automatically

## Requirements
- Python 3.10+
- Windows, Linux or macOS

## Run on Windows (Command Prompt)
```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Demo accounts
- Teacher: `teacher@classora.demo` / `Teacher123!`
- Student: `student@classora.demo` / `Student123!`
- Admin: `admin@classora.demo` / `Admin123!`

Change demo passwords and `SECRET_KEY` before any real deployment. This project is a classroom prototype, not production-hardened. Use only trusted files for demonstrations. Uploaded files are stored in `uploads/`; the SQLite database is created as `classora.db`.

## Project structure
- `app.py` — Flask routes, authentication, upload/download, notices
- `database.py` — SQLite schema and repository helpers
- `templates/` — HTML templates
- `static/style.css` — responsive interface styles
- `tests/test_app.py` — basic automated tests

## Academic integrity
This starter project was generated with AI assistance. Review it, understand it, test it, and declare AI use truthfully in your report. Replace team names/roll numbers and insert screenshots/results from your own run before submission.


## Student subject-folder dashboard

Students now land on a subject directory rather than a combined materials feed.
Select a subject to open its category folders (Notes, Exam/Syllabus, Assignment,
Project, Practical/Lab, and Other). Folder counts come from the materials table;
opening a folder filters files by both the selected subject and category. Search
runs within the selected subject. Student subject access is restricted to the
student's semester and section. Teacher/admin dashboard behavior is retained.
