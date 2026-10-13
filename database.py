"""SQLite access layer for CareerPath AI. All SQL is parameterized."""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL CHECK (length(full_name) BETWEEN 1 AND 120),
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    is_verified INTEGER NOT NULL DEFAULT 0 CHECK (is_verified IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE TABLE IF NOT EXISTS email_verifications (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code_hash TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts BETWEEN 0 AND 5),
    sent_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    used_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_email_verifications_user ON email_verifications(user_id, sent_at);
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    display_name TEXT NOT NULL CHECK (length(display_name) BETWEEN 1 AND 80),
    degree TEXT, field_of_study TEXT, education_level TEXT,
    career_interests TEXT, preferred_work_type TEXT, weekly_learning_time TEXT, learning_goals TEXT,
    selected_role_id INTEGER REFERENCES career_roles(id) ON DELETE SET NULL,
    is_demo INTEGER NOT NULL DEFAULT 0 CHECK (is_demo IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT
);
CREATE TABLE IF NOT EXISTS student_skills (
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    level INTEGER NOT NULL CHECK (level BETWEEN 0 AND 3),   -- self-reported
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    PRIMARY KEY (student_id, skill_id)
);
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'completed' CHECK (status IN ('completed','in_progress'))
);
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    name TEXT NOT NULL, description TEXT, technologies TEXT,
    status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','in_progress','completed'))
);
CREATE TABLE IF NOT EXISTS career_roles (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    overview TEXT,
    category TEXT NOT NULL DEFAULT 'other-technology'
);
CREATE TABLE IF NOT EXISTS career_role_skills (
    role_id INTEGER NOT NULL REFERENCES career_roles(id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    target_level INTEGER NOT NULL CHECK (target_level BETWEEN 1 AND 3),
    importance INTEGER NOT NULL CHECK (importance BETWEEN 1 AND 3),
    prerequisite_skill_id INTEGER REFERENCES skills(id),
    PRIMARY KEY (role_id, skill_id)
);
CREATE TABLE IF NOT EXISTS learning_resources (
    id INTEGER PRIMARY KEY,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    title TEXT NOT NULL, description TEXT,
    resource_type TEXT NOT NULL, url TEXT NOT NULL,
    cost TEXT NOT NULL DEFAULT 'unchecked' CHECK (cost IN ('free','paid','unchecked'))
);
CREATE TABLE IF NOT EXISTS roadmap_milestones (
    id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES career_roles(id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(id),
    position INTEGER NOT NULL,
    title TEXT NOT NULL, objective TEXT, estimated_hours INTEGER,
    status TEXT NOT NULL DEFAULT 'not_started'
        CHECK (status IN ('not_started','in_progress','completed')),
    notes TEXT,
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    UNIQUE (student_id, role_id, skill_id)
);
CREATE TABLE IF NOT EXISTS milestone_resources (
    milestone_id INTEGER NOT NULL REFERENCES roadmap_milestones(id) ON DELETE CASCADE,
    resource_id INTEGER NOT NULL REFERENCES learning_resources(id) ON DELETE CASCADE,
    PRIMARY KEY (milestone_id, resource_id)
);
CREATE TABLE IF NOT EXISTS progress_activity (
    id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE TABLE IF NOT EXISTS assessment_attempts (   -- quiz evidence, kept apart from self-reported levels
    id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    score INTEGER NOT NULL, max_score INTEGER NOT NULL CHECK (max_score > 0),
    taken_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_student_skills_student ON student_skills(student_id);
CREATE INDEX IF NOT EXISTS idx_milestones_student ON roadmap_milestones(student_id, role_id);
CREATE INDEX IF NOT EXISTS idx_activity_student ON progress_activity(student_id, created_at);
CREATE INDEX IF NOT EXISTS idx_resources_skill ON learning_resources(skill_id);
"""


def get_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite ignores FKs unless enabled per connection
    return conn


def init_db(db_path):
    """Create tables if missing. Safe to call on every start; never wipes data."""
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        # Safe migration for databases created by the original Skillora build.
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(career_roles)")}
        if "category" not in columns:
            conn.execute("ALTER TABLE career_roles ADD COLUMN category TEXT NOT NULL DEFAULT 'other-technology'")
        student_columns = {row["name"] for row in conn.execute("PRAGMA table_info(students)")}
        if "preferred_work_type" not in student_columns:
            conn.execute("ALTER TABLE students ADD COLUMN preferred_work_type TEXT")
        if "weekly_learning_time" not in student_columns:
            conn.execute("ALTER TABLE students ADD COLUMN weekly_learning_time TEXT")
        if "user_id" not in student_columns:
            conn.execute("ALTER TABLE students ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE")
        conn.commit()
    finally:
        conn.close()
