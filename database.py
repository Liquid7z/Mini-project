import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash

DB_PATH = Path(__file__).with_name("classora.db")

def connect():
    """Create a row-aware SQLite connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('teacher','student','admin')),
            semester TEXT NOT NULL DEFAULT '3',
            section TEXT NOT NULL DEFAULT 'E'
        );
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE,
            semester TEXT NOT NULL,
            section TEXT NOT NULL,
            teacher_id INTEGER,
            FOREIGN KEY(teacher_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            category TEXT NOT NULL,
            subject_id INTEGER NOT NULL,
            semester TEXT NOT NULL,
            section TEXT NOT NULL,
            filename TEXT NOT NULL,
            stored_name TEXT NOT NULL,
            uploaded_by INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(subject_id) REFERENCES subjects(id),
            FOREIGN KEY(uploaded_by) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            semester TEXT NOT NULL,
            section TEXT NOT NULL,
            posted_by INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(posted_by) REFERENCES users(id)
        );
        """)
        count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count == 0:
            users = [
                ("Demo Teacher", "teacher@classora.demo", generate_password_hash("Teacher123!"), "teacher", "3", "E"),
                ("Demo Student", "student@classora.demo", generate_password_hash("Student123!"), "student", "3", "E"),
                ("Demo Admin", "admin@classora.demo", generate_password_hash("Admin123!"), "admin", "3", "E"),
            ]
            db.executemany("INSERT INTO users(name,email,password_hash,role,semester,section) VALUES(?,?,?,?,?,?)", users)
            teacher_id = db.execute("SELECT id FROM users WHERE email='teacher@classora.demo'").fetchone()[0]
            subjects = [
                ("Programming with Python", "BTCS2101", "3", "E", teacher_id),
                ("Data Structures", "BTCS2102", "3", "E", teacher_id),
                ("Digital Electronics", "BTCS2103", "3", "E", teacher_id),
            ]
            db.executemany("INSERT INTO subjects(name,code,semester,section,teacher_id) VALUES(?,?,?,?,?)", subjects)
        db.commit()

def get_user_by_email(email):
    with connect() as db:
        return db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()

def list_subjects(user):
    with connect() as db:
        if user["role"] == "teacher":
            return db.execute("SELECT * FROM subjects WHERE teacher_id=? ORDER BY name", (user["id"],)).fetchall()
        return db.execute("SELECT * FROM subjects WHERE semester=? AND section=? ORDER BY name",
                          (user["semester"], user["section"])).fetchall()

def list_materials(user, search="", category="", subject_id=""):
    query = """SELECT m.*, s.name AS subject_name, s.code AS subject_code, u.name AS uploader
               FROM materials m JOIN subjects s ON s.id=m.subject_id
               JOIN users u ON u.id=m.uploaded_by
               WHERE 1=1"""
    args = []
    if user["role"] == "student":
        query += " AND m.semester=? AND m.section=?"
        args += [user["semester"], user["section"]]
    if search:
        query += " AND (m.title LIKE ? OR m.description LIKE ? OR s.name LIKE ? OR s.code LIKE ?)"
        args += [f"%{search}%"] * 4
    if category:
        query += " AND m.category=?"; args.append(category)
    if subject_id:
        query += " AND m.subject_id=?"; args.append(subject_id)
    query += " ORDER BY m.created_at DESC"
    with connect() as db:
        return db.execute(query, args).fetchall()

def list_notices(user):
    with connect() as db:
        if user["role"] == "student":
            return db.execute("""SELECT n.*, u.name AS author FROM notices n JOIN users u ON u.id=n.posted_by
              WHERE (n.semester=? OR n.semester='All') AND (n.section=? OR n.section='All')
              ORDER BY n.created_at DESC""", (user["semester"], user["section"])).fetchall()
        return db.execute("""SELECT n.*, u.name AS author FROM notices n JOIN users u ON u.id=n.posted_by
              ORDER BY n.created_at DESC LIMIT 50""").fetchall()
