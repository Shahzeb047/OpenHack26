"""CareerPath AI - Flask application factory (local single-student prototype)."""
import secrets
import hashlib
import hmac
import os
import smtplib
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from functools import wraps
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, g, session
from werkzeug.security import check_password_hash, generate_password_hash
from database import init_db, get_connection
from services import career_catalog as cat
from services.skill_analyzer import analyze
from services.roadmap_generator import sync

BASE_DIR = Path(__file__).resolve().parent
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(path, override=False):
        """Small fallback so direct system-Python launches still work."""
        env_path = Path(path)
        if not env_path.exists():
            return False
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip().strip("\"'")
            if override or key not in os.environ:
                os.environ[key] = value
        return True

load_dotenv(BASE_DIR / ".env", override=False)
STATUSES = ("not_started", "in_progress", "completed")
DEMO_LEVELS = {"SQL": 1, "Python": 2, "Data cleaning": 1, "Statistics": 0, "Data visualization": 0}


def create_app(test_config=None):
    app = Flask(__name__, instance_path=str(BASE_DIR / "instance"))
    app.config.from_mapping(DATABASE=str(Path(app.instance_path) / "skillora.db"),
                            SECRET_KEY=os.environ.get("CAREERPATH_SECRET_KEY", secrets.token_hex(32)),
                            SMTP_HOST=os.environ.get("CAREERPATH_SMTP_HOST", ""),
                            SMTP_PORT=int(os.environ.get("CAREERPATH_SMTP_PORT", "587")),
                            SMTP_USERNAME=os.environ.get("CAREERPATH_SMTP_USERNAME", ""),
                            SMTP_PASSWORD=os.environ.get("CAREERPATH_SMTP_PASSWORD", ""),
                            SMTP_FROM=os.environ.get("CAREERPATH_SMTP_FROM", ""),
                            DEV_EMAIL_MODE=os.environ.get("CAREERPATH_DEV_EMAIL", "0") == "1",
                            MAIL_SUPPRESS_SEND=False)
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(exist_ok=True)
    init_db(app.config["DATABASE"])
    with closing_conn(app) as c:
        cat.seed(c)
    app.jinja_env.globals.update(LEVELS=cat.LEVELS, SKILLS=cat.SKILLS)

    def db():
        if "db" not in g:
            g.db = get_connection(app.config["DATABASE"])
        return g.db

    def current_user():
        user_id = session.get("user_id")
        if not user_id:
            return None
        return db().execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()

    def csrf_token():
        token = session.get("csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            session["csrf_token"] = token
        return token

    def require_csrf():
        supplied = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
        if not supplied or not hmac.compare_digest(supplied, csrf_token()):
            return jsonify(error="Invalid request token."), 400
        return None

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user():
                if request.path.startswith("/api/"):
                    return jsonify(error="Authentication required."), 401
                flash("Sign in to access your private career workspace.", "error")
                return redirect(url_for("login", next=request.full_path))
            return view(*args, **kwargs)
        return wrapped

    @app.context_processor
    def auth_context():
        return {"current_user": current_user(), "csrf_token": csrf_token()}

    def send_verification_email(user, code):
        if app.config["MAIL_SUPPRESS_SEND"]:
            return
        if app.config["DEV_EMAIL_MODE"]:
            dev_mail = Path(app.instance_path) / "dev-mail.log"
            with dev_mail.open("a", encoding="utf-8") as out:
                out.write(f"{datetime.now(timezone.utc).isoformat()} | {user['email']} | verification code: {code}\n")
            app.logger.warning(
                "SMTP is not configured; development verification code written to %s. "
                "Configure real SMTP before deployment.",
                dev_mail,
            )
            return
        required = ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM")
        if not all(app.config.get(key) for key in required):
            raise RuntimeError("Email delivery is not configured. Set the SMTP environment variables.")
        message = EmailMessage()
        message["Subject"] = "Verify your CareerPath AI account"
        message["From"] = app.config["SMTP_FROM"]
        message["To"] = user["email"]
        message.set_content(f"Your CareerPath AI verification code is {code}. It expires in 10 minutes.")
        smtp_class = smtplib.SMTP_SSL if app.config["SMTP_PORT"] == 465 else smtplib.SMTP
        with smtp_class(app.config["SMTP_HOST"], app.config["SMTP_PORT"], timeout=15) as smtp:
            if app.config["SMTP_PORT"] != 465:
                smtp.starttls()
            smtp.login(app.config["SMTP_USERNAME"], app.config["SMTP_PASSWORD"])
            smtp.send_message(message)

    def issue_verification(user):
        recent = db().execute(
            "SELECT sent_at FROM email_verifications WHERE user_id=? ORDER BY id DESC LIMIT 1", (user["id"],)
        ).fetchone()
        if recent:
            sent = datetime.strptime(recent["sent_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - sent < timedelta(seconds=60):
                raise ValueError("Please wait 60 seconds before requesting another code.")
        code = f"{secrets.randbelow(1000000):06d}"
        digest = hashlib.sha256(code.encode()).hexdigest()
        db().execute("UPDATE email_verifications SET used_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE user_id=? AND used_at IS NULL",
                     (user["id"],))
        db().execute("INSERT INTO email_verifications (user_id,code_hash,expires_at) VALUES (?,?,?)",
                     (user["id"], digest, (datetime.now(timezone.utc) + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")))
        send_verification_email(user, code)
        db().commit()
        return code if app.config["DEV_EMAIL_MODE"] else None

    @app.teardown_appcontext
    def close(_):
        d = g.pop("db", None)
        if d: d.close()

    def log(msg):
        student = current_student()
        if student:
            db().execute("INSERT INTO progress_activity (student_id, message) VALUES (?,?)", (student["id"], msg))

    def current_student():
        user = current_user()
        return db().execute("SELECT * FROM students WHERE user_id=?", (user["id"],)).fetchone() if user else None

    def state():
        c = db()
        student = current_student()
        role = None; analysis = None
        if student and student["selected_role_id"]:
            role = c.execute("SELECT * FROM career_roles WHERE id=?", (student["selected_role_id"],)).fetchone()
            rows = [dict(r) for r in c.execute("""SELECT crs.skill_id, s.name, s.description why, crs.target_level target,
                crs.importance, crs.prerequisite_skill_id prereq_id FROM career_role_skills crs
                JOIN skills s ON s.id=crs.skill_id WHERE crs.role_id=? ORDER BY crs.importance DESC, s.name""", (role["id"],))]
            levels = {r["skill_id"]: r["level"] for r in c.execute(
                "SELECT skill_id, level FROM student_skills WHERE student_id=?", (student["id"],))}
            analysis = analyze(rows, levels)
        return student, role, analysis

    def milestones(role_id):
        student = current_student()
        return db().execute("""SELECT m.*, s.name skill FROM roadmap_milestones m JOIN skills s ON s.id=m.skill_id
                WHERE m.student_id=? AND m.role_id=? ORDER BY m.position""", (student["id"], role_id)).fetchall()

    def progress(role_id):
        ms = milestones(role_id); done = sum(m["status"] == "completed" for m in ms)
        return {"total": len(ms), "completed": done, "percent": round(100 * done / len(ms)) if ms else 0}

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user():
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            invalid = require_csrf()
            if invalid:
                return invalid
            name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            confirm = request.form.get("confirm_password", "")
            if not name or len(name) > 120 or "@" not in email or len(email) > 254:
                flash("Enter a valid name and email address.", "error")
                return render_template("register.html"), 400
            if len(password) < 8 or password != confirm:
                flash("Passwords must match and contain at least 8 characters.", "error")
                return render_template("register.html"), 400
            existing = db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
            if existing and existing["is_verified"]:
                flash("An account with that email already exists. Sign in instead.", "error")
                return redirect(url_for("login"))
            if existing:
                user_id = existing["id"]
                db().execute("UPDATE users SET full_name=?, password_hash=?, updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id=?",
                             (name, generate_password_hash(password), user_id))
            else:
                cur = db().execute("INSERT INTO users (full_name,email,password_hash) VALUES (?,?,?)",
                                   (name, email, generate_password_hash(password)))
                user_id = cur.lastrowid
            db().execute("INSERT OR IGNORE INTO students (user_id,display_name) VALUES (?,?)", (user_id, name))
            db().commit()
            flash("Account created. You can now sign in.", "ok")
            return redirect(url_for("login"))
        return render_template("register.html")

    @app.route("/verify", methods=["GET", "POST"])
    def verify():
        user_id = session.get("pending_user_id")
        user = db().execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone() if user_id else None
        if not user:
            return redirect(url_for("register"))
        if request.method == "POST":
            invalid = require_csrf()
            if invalid:
                return invalid
            code = request.form.get("code", "").strip()
            record = db().execute("""SELECT * FROM email_verifications WHERE user_id=? AND used_at IS NULL
                ORDER BY id DESC LIMIT 1""", (user_id,)).fetchone()
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if not record or record["attempts"] >= 5 or record["expires_at"] < now:
                flash("That code is invalid or expired. Request a new code.", "error")
                return render_template("verify.html", email=user["email"]), 400
            if not hmac.compare_digest(record["code_hash"], hashlib.sha256(code.encode()).hexdigest()):
                db().execute("UPDATE email_verifications SET attempts=attempts+1 WHERE id=?", (record["id"],))
                db().commit()
                flash("Incorrect verification code.", "error")
                return render_template("verify.html", email=user["email"]), 400
            db().execute("UPDATE users SET is_verified=1 WHERE id=?", (user_id,))
            db().execute("UPDATE email_verifications SET used_at=? WHERE id=?", (now, record["id"]))
            db().execute("INSERT OR IGNORE INTO students (user_id,display_name) VALUES (?,?)", (user_id, user["full_name"]))
            db().commit()
            session.clear()
            session["user_id"] = user_id
            csrf_token()
            return redirect(url_for("dashboard"))
        return render_template("verify.html", email=user["email"])

    @app.post("/resend-verification")
    def resend_verification():
        user_id = session.get("pending_user_id")
        user = db().execute("SELECT * FROM users WHERE id=? AND is_verified=0", (user_id,)).fetchone()
        invalid = require_csrf()
        if invalid:
            return invalid
        if not user:
            return redirect(url_for("register"))
        try:
            issue_verification(user)
        except (ValueError, RuntimeError, OSError, smtplib.SMTPException) as exc:
            message = "Email could not be sent. Check your SMTP settings and try again."
            if isinstance(exc, (ValueError, RuntimeError)):
                message = str(exc)
            app.logger.error("Verification email resend failed: %s", exc.__class__.__name__)
            flash(message, "error")
        else:
            flash("A new verification code was sent.", "ok")
        return redirect(url_for("verify"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user():
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            invalid = require_csrf()
            if invalid:
                return invalid
            email = request.form.get("email", "").strip().lower()
            user = db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
            if not user or not check_password_hash(user["password_hash"], request.form.get("password", "")):
                flash("Email or password is incorrect.", "error")
                return render_template("login.html"), 401
            session.clear()
            session["user_id"] = user["id"]
            csrf_token()
            return redirect(request.form.get("next") or url_for("dashboard"))
        return render_template("login.html")

    @app.post("/logout")
    def logout():
        invalid = require_csrf()
        if invalid:
            return invalid
        session.clear()
        return redirect(url_for("index"))

    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        student = current_student()
        if request.method == "POST":
            invalid = require_csrf()
            if invalid:
                return invalid
            f = {k: request.form.get(k, "").strip() for k in
                 ("display_name", "degree", "field_of_study", "education_level", "career_interests",
                  "preferred_work_type", "weekly_learning_time", "learning_goals")}
            if not f["display_name"] or len(f["display_name"]) > 80:
                flash("Enter a display name of 1 to 80 characters.", "error")
                return render_template("profile.html", student=f), 400
            if student:
                db().execute("""UPDATE students SET display_name=?, degree=?, field_of_study=?, education_level=?, career_interests=?,
                    preferred_work_type=?, weekly_learning_time=?, learning_goals=?,
                    updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id=?""", (*f.values(), student["id"]))
            else:
                db().execute("""INSERT INTO students (id, display_name, degree, field_of_study, education_level, career_interests,
                    preferred_work_type, weekly_learning_time, learning_goals, user_id) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                             (*f.values(), current_user()["id"]))
            log("Saved profile"); db().commit()
            flash("Profile saved.", "ok")
            return redirect(url_for("careers"))
        return render_template("profile.html", student=student)

    @app.route("/careers", methods=["GET", "POST"])
    @login_required
    def careers():
        student = current_student()
        if request.method == "POST":
            invalid = require_csrf()
            if invalid:
                return invalid
            custom_title = request.form.get("custom_title", "").strip()
            if custom_title:
                raw = request.form.get("custom_skills", "").strip()
                if not 2 <= len(custom_title) <= 100 or not raw:
                    flash("Enter a career title and at least two required skills.", "error")
                    return redirect(url_for("careers"))
                if not student:
                    flash("Create your profile first, then add a custom career.", "error")
                    return redirect(url_for("profile"))
                slug = "custom-" + secrets.token_hex(6)
                db().execute("INSERT INTO career_roles (slug,title,overview,category) VALUES (?,?,?,?)",
                             (slug, custom_title, "User-entered target based on your own requirements.", "custom"))
                role_id = db().execute("SELECT id FROM career_roles WHERE slug=?", (slug,)).fetchone()["id"]
                names = [n.strip() for n in raw.split(",") if n.strip()]
                for pos, name in enumerate(dict.fromkeys(names), 1):
                    db().execute("INSERT OR IGNORE INTO skills (name, description) VALUES (?,?)",
                                 (name[:80], "User-entered requirement; not verified employer data."))
                    skill_id = db().execute("SELECT id FROM skills WHERE name=?", (name[:80],)).fetchone()["id"]
                    db().execute("INSERT OR IGNORE INTO career_role_skills VALUES (?,?,?,?,?)",
                                 (role_id, skill_id, 2, 3 if pos <= 2 else 2, None))
                db().execute("UPDATE students SET selected_role_id=? WHERE id=?", (role_id, student["id"]))
                log(f"Added custom career: {custom_title}"); db().commit()
                _, _, a = state(); sync(db(), student["id"], role_id, a["items"])
                return redirect(url_for("assessment"))
            role = db().execute("SELECT * FROM career_roles WHERE slug=?", (request.form.get("slug", ""),)).fetchone()
            if not student or not role:
                flash("Create your profile first, then choose one of the listed careers.", "error")
                return redirect(url_for("profile"))
            db().execute("UPDATE students SET selected_role_id=? WHERE id=?", (role["id"], student["id"]))
            log(f"Selected career: {role['title']}"); db().commit()
            _, _, a = state(); sync(db(), student["id"], role["id"], a["items"])
            return redirect(url_for("assessment"))
        query = request.args.get("q", "").strip().lower()
        category = request.args.get("category", "").strip()
        roles = {slug: role for slug, role in cat.ROLES.items()
                 if (not query or query in role["title"].lower() or query in role["overview"].lower())
                 and (not category or role["category"] == category)}
        return render_template("careers.html", roles=roles, categories=cat.categories(), student=student,
                               selected=state()[1], query=query, category=category)

    @app.route("/assessment", methods=["GET", "POST"])
    @login_required
    def assessment():
        student, role, a = state()
        if not role:
            flash("Choose a career first.", "error"); return redirect(url_for("careers"))
        if request.method == "POST":
            invalid = require_csrf()
            if invalid:
                return invalid
            new = {}
            for i in a["items"]:
                v = request.form.get(f"skill_{i['skill_id']}", "")
                if v == "":
                    continue
                if v not in ("0", "1", "2", "3"):
                    flash("Every skill needs a level from 0 to 3.", "error")
                    return render_template("assessment.html", a=a, role=role), 400
                new[i["skill_id"]] = int(v)
            for sk, lv in new.items():
                db().execute("""INSERT INTO student_skills (student_id, skill_id, level) VALUES (?,?,?)
                    ON CONFLICT(student_id, skill_id) DO UPDATE SET level=excluded.level,
                    updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now')""", (student["id"], sk, lv))
            log("Updated self-reported skill levels"); db().commit()
            _, _, a = state(); sync(db(), student["id"], role["id"], a["items"])
            flash("Analysis and roadmap updated.", "ok")
            return redirect(url_for("dashboard"))
        return render_template("assessment.html", a=a, role=role)

    @app.route("/dashboard")
    @login_required
    def dashboard():
        student, role, a = state()
        ctx = {"student": student, "role": role, "a": a}
        if role:
            ms = milestones(role["id"])
            alternatives = db().execute("""SELECT cr.title, cr.slug, COUNT(*) overlap
                FROM career_role_skills current_skills
                JOIN career_role_skills other_skills ON other_skills.skill_id=current_skills.skill_id
                JOIN career_roles cr ON cr.id=other_skills.role_id
                WHERE current_skills.role_id=? AND other_skills.role_id<>?
                GROUP BY cr.id ORDER BY overlap DESC, cr.title LIMIT 4""",
                (role["id"], role["id"])).fetchall()
            ctx.update(p=progress(role["id"]), learning=[m for m in ms if m["status"] == "in_progress"],
                       next=next((m for m in ms if m["status"] != "completed"), None),
                       project=cat.role_info(role["slug"], role["title"])["project"],
                       alternatives=alternatives,
                       skill_count=db().execute("SELECT COUNT(*) FROM student_skills WHERE student_id=?", (student["id"],)).fetchone()[0],
                       project_count=db().execute("SELECT COUNT(*) FROM projects WHERE student_id=? AND status='completed'", (student["id"],)).fetchone()[0],
                       activity=db().execute("SELECT * FROM progress_activity WHERE student_id=? ORDER BY id DESC LIMIT 6", (student["id"],)).fetchall())
        return render_template("dashboard.html", **ctx)

    @app.route("/roadmap")
    @login_required
    def roadmap():
        student, role, a = state()
        if not role:
            flash("Choose a career first.", "error"); return redirect(url_for("careers"))
        ms = milestones(role["id"])
        res = {m["id"]: db().execute("SELECT * FROM learning_resources WHERE skill_id=?", (m["skill_id"],)).fetchall() for m in ms}
        return render_template("roadmap.html", role=role, ms=ms, res=res, p=progress(role["id"]),
                               project=cat.role_info(role["slug"], role["title"])["project"])

    @app.route("/api/milestones/<int:mid>", methods=["PATCH"])
    @login_required
    def update_milestone(mid):
        student = current_student()
        m = db().execute("SELECT * FROM roadmap_milestones WHERE id=? AND student_id=?", (mid, student["id"])).fetchone()
        if not m:
            return jsonify(error="Milestone not found."), 404
        status = (request.get_json(silent=True) or {}).get("status")
        invalid = require_csrf()
        if invalid:
            return invalid
        if status not in STATUSES:
            return jsonify(error="Status must be not_started, in_progress or completed."), 400
        db().execute("UPDATE roadmap_milestones SET status=?, updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id=?", (status, mid))
        log(f"{m['title']}: {status.replace('_', ' ')}"); db().commit()
        return jsonify(status=status, **progress(m["role_id"]))

    @app.route("/demo", methods=["POST"])
    @login_required
    def demo():
        c = db(); student = current_student()
        c.execute("DELETE FROM students WHERE id=?", (student["id"],))
        role = c.execute("SELECT id FROM career_roles WHERE slug='data-analyst'").fetchone()
        c.execute("""INSERT INTO students (id, user_id, display_name, degree, field_of_study, education_level, learning_goals, selected_role_id, is_demo)
            VALUES (?,?,?,?,?,?,?,?,1)""", (student["id"], current_user()["id"], "Demo Student (fictional)", "BS Software Engineering", "Computer Science",
                                          "Semester 5", "Land a junior data role", role["id"]))
        for n, lv in DEMO_LEVELS.items():
            c.execute("INSERT INTO student_skills (student_id, skill_id, level) SELECT ?, id, ? FROM skills WHERE name=?", (student["id"], lv, n))
        log("Loaded fictional demo student"); c.commit()
        _, _, a = state(); sync(c, student["id"], role["id"], a["items"])
        return redirect(url_for("dashboard"))

    @app.route("/reset", methods=["POST"])
    @login_required
    def reset():
        invalid = require_csrf()
        if invalid:
            return invalid
        db().execute("DELETE FROM students WHERE id=?", (current_student()["id"],)); db().commit()
        flash("All your saved data was deleted.", "ok")
        return redirect(url_for("index"))

    @app.route("/health")
    def health():
        return jsonify(status="ok")

    @app.errorhandler(404)
    def not_found(_):
        return render_template("coming_soon.html", title="Page not found", phase=None), 404

    return app


def closing_conn(app):
    from contextlib import closing
    return closing(get_connection(app.config["DATABASE"]))


if __name__ == "__main__":
    create_app().run(debug=True)
