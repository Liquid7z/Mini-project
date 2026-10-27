import os
import uuid
from functools import wraps
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, abort
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from database import init_db, connect, get_user_by_email, list_subjects, list_materials, list_notices

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "ppt", "pptx", "txt", "png", "jpg", "jpeg"}
CATEGORIES = ["Notes", "Exam/Syllabus", "Assignment", "Project", "Practical/Lab", "Other"]

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("CLASSORA_SECRET_KEY", "dev-only-change-this-secret")
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024
UPLOAD_DIR.mkdir(exist_ok=True)
init_db()

def current_user():
    if "user_id" not in session:
        return None
    with connect() as db:
        return db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


from functools import wraps

def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()

            if not user:
                return redirect(url_for("login"))

            if user["role"] not in roles:
                abort(403)

            return fn(*args, **kwargs)

        return wrapper
    return decorator


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.context_processor
def inject_globals():
    return {"current_user": current_user(), "categories": CATEGORIES}

@app.route("/")
def index():
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    search = request.args.get("q", "").strip()[:100]
    category = request.args.get("category", "")
    subject_id = request.args.get("subject", "")
    if category not in CATEGORIES:
        category = ""

    materials = list_materials(user, search, category, subject_id)
    notices = list_notices(user)
    subjects = list_subjects(user)

    with connect() as db:
        if user["role"] == "student":
            material_count = db.execute(
                "SELECT COUNT(*) FROM materials WHERE semester=? AND section=?",
                (user["semester"], user["section"])
            ).fetchone()[0]
            notice_count = db.execute(
                """SELECT COUNT(*) FROM notices
                   WHERE (semester=? OR semester='All') AND (section=? OR section='All')""",
                (user["semester"], user["section"])
            ).fetchone()[0]
        else:
            material_count = db.execute("SELECT COUNT(*) FROM materials").fetchone()[0]
            notice_count = db.execute("SELECT COUNT(*) FROM notices").fetchone()[0]

    return render_template(
        "dashboard.html", materials=materials, notices=notices, subjects=subjects,
        search=search, selected_category=category, selected_subject=subject_id,
        material_count=material_count, notice_count=notice_count,
        subject_count=len(subjects), subject_view=None, folder_counts={},
        categories=CATEGORIES
    )


@app.route("/subject/<int:subject_id>")
@login_required
def subject_detail(subject_id):
    user = current_user()
    with connect() as db:
        subject = db.execute("SELECT * FROM subjects WHERE id=?", (subject_id,)).fetchone()
    if not subject:
        abort(404)
    if user["role"] == "student" and (
        subject["semester"] != user["semester"] or subject["section"] != user["section"]
    ):
        abort(403)
    if user["role"] == "teacher" and subject["teacher_id"] != user["id"]:
        abort(403)

    category = request.args.get("category", "")
    if category not in CATEGORIES:
        category = ""
    search = request.args.get("q", "").strip()[:100]

    materials = list_materials(user, search, category, str(subject_id))
    notices = list_notices(user)
    subjects = list_subjects(user)

    with connect() as db:
        folder_counts = {}
        for folder in CATEGORIES:
            row = db.execute(
                "SELECT COUNT(*) FROM materials WHERE subject_id=? AND category=?",
                (subject_id, folder)
            ).fetchone()
            folder_counts[folder] = row[0]
        material_count = db.execute(
            "SELECT COUNT(*) FROM materials WHERE subject_id=?", (subject_id,)
        ).fetchone()[0]
        notice_count = db.execute("SELECT COUNT(*) FROM notices").fetchone()[0]

    return render_template(
        "dashboard.html", materials=materials, notices=notices, subjects=subjects,
        search=search, selected_category=category, selected_subject=str(subject_id),
        material_count=material_count, notice_count=notice_count,
        subject_count=len(subjects), subject_view=subject, folder_counts=folder_counts,
        categories=CATEGORIES
    )

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_user_by_email(email)
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("index"))
        flash("Email or password is incorrect.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("login"))

@app.route("/upload", methods=["GET", "POST"])
@login_required
@roles_required("teacher", "admin")
def upload():
    user = current_user()
    subjects = list_subjects(user)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "")
        subject_id = request.form.get("subject_id", "")
        semester = request.form.get("semester", "").strip()
        section = request.form.get("section", "").strip().upper()
        file = request.files.get("file")
        if not title or not subject_id or not semester or not section or not file or not file.filename:
            flash("Complete all required fields and select a file.", "danger")
            return render_template("upload.html", subjects=subjects)
        if category not in CATEGORIES:
            flash("Choose a valid material category.", "danger")
            return render_template("upload.html", subjects=subjects)
        with connect() as db:
            subject = db.execute("SELECT * FROM subjects WHERE id=?", (subject_id,)).fetchone()
        if not subject or (user["role"] == "teacher" and subject["teacher_id"] != user["id"]):
            abort(403)
        if (semester, section) != (subject["semester"], subject["section"]):
            flash("Semester and section must match the selected subject's assigned class.", "danger")
            return render_template("upload.html", subjects=subjects)
        if not allowed_file(file.filename):
            flash("Unsupported file type. Use PDF, Office documents, TXT or images.", "danger")
            return render_template("upload.html", subjects=subjects)
        original = secure_filename(file.filename)
        stored = f"{uuid.uuid4().hex}_{original}"
        try:
            file.save(UPLOAD_DIR / stored)
            with connect() as db:
                db.execute("""INSERT INTO materials(title,description,category,subject_id,semester,section,
                              filename,stored_name,uploaded_by) VALUES(?,?,?,?,?,?,?,?,?)""",
                           (title, description, category, subject_id, semester, section, original, stored, user["id"]))
                db.commit()
        except (OSError, ValueError) as exc:
            (UPLOAD_DIR / stored).unlink(missing_ok=True)
            flash(f"Could not save material: {exc}", "danger")
            return render_template("upload.html", subjects=subjects)
        flash("Material uploaded to the selected subject folder.", "success")
        return redirect(url_for("index"))
    return render_template("upload.html", subjects=subjects)

@app.route("/notices/new", methods=["GET", "POST"])
@login_required
@roles_required("teacher", "admin")
def new_notice():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        semester = request.form.get("semester", "").strip()
        section = request.form.get("section", "").strip()
        if not all([title, body, semester, section]):
            flash("Please complete every notice field.", "danger")
        else:
            with connect() as db:
                db.execute("INSERT INTO notices(title,body,semester,section,posted_by) VALUES(?,?,?,?,?)",
                           (title, body, semester, section, current_user()["id"]))
                db.commit()
            flash("Notice published.", "success")
            return redirect(url_for("index"))
    return render_template("notice.html")

@app.route("/download/<int:material_id>")
@login_required
def download(material_id):
    user = current_user()
    with connect() as db:
        material = db.execute("SELECT * FROM materials WHERE id=?", (material_id,)).fetchone()
    if not material: abort(404)
    if user["role"] == "student" and (material["semester"] != user["semester"] or material["section"] != user["section"]):
        abort(403)
    return send_from_directory(UPLOAD_DIR, material["stored_name"], as_attachment=True, download_name=material["filename"])

@app.errorhandler(403)
def forbidden(_error):
    return render_template("error.html", code=403, message="You do not have permission to access this resource."), 403

@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="The requested page or material was not found."), 404

@app.errorhandler(413)
def too_large(_error):
    return render_template("error.html", code=413, message="The upload exceeds the 12 MB limit."), 413

if __name__ == "__main__":
    app.run(debug=True)
