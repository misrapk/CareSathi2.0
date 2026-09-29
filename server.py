from __future__ import annotations

import hashlib
import hmac
import json
import mimetypes
import os
import secrets
import sqlite3
import sys
import unicodedata
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
PUBLIC_DIR = ROOT / "public"
DB_PATH = Path(os.environ.get("CARESATHI_DB", ROOT / "caresathi.db"))
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_POSTGRES = bool(DATABASE_URL)
DEMO_MODE = os.environ.get("CARESATHI_DEMO_MODE", "1" if not USE_POSTGRES else "0") == "1"
ADMIN_EMAIL = os.environ.get("CARESATHI_ADMIN_EMAIL", "").strip().lower()
ADMIN_PASSWORD = os.environ.get("CARESATHI_ADMIN_PASSWORD", "")
SESSION_HOURS = 72

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # Local development intentionally has no external dependencies.
    psycopg = None
    dict_row = None

DB_INTEGRITY_ERRORS = (sqlite3.IntegrityError,) if psycopg is None else (sqlite3.IntegrityError, psycopg.IntegrityError)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_city(value: str) -> str:
    """Normalize common spelling variants while preserving the user's display value."""
    normalized = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode().lower()
    normalized = "".join(character for character in normalized if character.isalnum())
    aliases = {
        "bangalore": "bengaluru",
        "bombay": "mumbai",
        "calcutta": "kolkata",
        "madras": "chennai",
    }
    return aliases.get(normalized, normalized)


def cities_match(first: str, second: str) -> bool:
    left, right = normalize_city(first), normalize_city(second)
    if not left or not right:
        return False
    if left == right:
        return True
    # Handles small registration typos such as "Ahmedbad" vs "Ahmedabad".
    return min(len(left), len(right)) >= 5 and SequenceMatcher(None, left, right).ratio() >= 0.84


def password_hash(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 180_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, expected = stored.split("$", 1)
        actual = password_hash(password, salt).split("$", 1)[1]
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


class ClosingConnection(sqlite3.Connection):
    """Commit or roll back and always release the database file handle."""

    def __exit__(self, exc_type, exc_value, traceback):
        result = super().__exit__(exc_type, exc_value, traceback)
        self.close()
        return result


class PostgresConnection:
    """Small DB-API adapter so the application can keep SQLite-style placeholders."""

    def __init__(self, url: str):
        self.connection = psycopg.connect(url, row_factory=dict_row)

    def execute(self, statement: str, params: tuple = ()):
        return self.connection.execute(statement.replace("?", "%s"), params)

    def __enter__(self):
        self.connection.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self.connection.__exit__(exc_type, exc_value, traceback)

    def close(self):
        self.connection.close()


def connect():
    if USE_POSTGRES:
        if psycopg is None:
            raise RuntimeError("DATABASE_URL is set, but psycopg is not installed. Run: pip install -r requirements.txt")
        return PostgresConnection(DATABASE_URL)
    db = sqlite3.connect(DB_PATH, factory=ClosingConnection)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def execute_script(db, script: str) -> None:
    if USE_POSTGRES:
        postgres_script = script.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY").replace(" COLLATE NOCASE", "")
        for statement in postgres_script.split(";"):
            if statement.strip():
                db.execute(statement)
    else:
        db.executescript(script)


def table_columns(db, table: str) -> set[str]:
    if USE_POSTGRES:
        rows = db.execute(
            "SELECT column_name AS name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s",
            (table,),
        ).fetchall()
    else:
        rows = db.execute(f"PRAGMA table_info({table})").fetchall()
    return {row["name"] for row in rows}


def insert_and_get_id(db, statement: str, params: tuple) -> int:
    if USE_POSTGRES:
        return db.execute(f"{statement} RETURNING id", params).fetchone()["id"]
    return db.execute(statement, params).lastrowid


def init_db() -> None:
    with connect() as db:
        execute_script(db,
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                phone TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('family', 'caretaker')),
                city TEXT NOT NULL DEFAULT '',
                verified INTEGER NOT NULL DEFAULT 0,
                rating REAL NOT NULL DEFAULT 0,
                jobs_completed INTEGER NOT NULL DEFAULT 0,
                headline TEXT NOT NULL DEFAULT 'Compassionate hospital companion',
                experience_years INTEGER NOT NULL DEFAULT 1,
                languages TEXT NOT NULL DEFAULT 'Hindi, English',
                hourly_rate INTEGER NOT NULL DEFAULT 150,
                skills TEXT NOT NULL DEFAULT 'General companionship',
                credential_badge TEXT NOT NULL DEFAULT 'Companion verified',
                credential_verified INTEGER NOT NULL DEFAULT 0,
                rating_count INTEGER NOT NULL DEFAULT 0,
                availability_hours TEXT NOT NULL DEFAULT 'Mon–Sun · 08:00–20:00',
                preferred_hospitals TEXT NOT NULL DEFAULT '',
                unavailable_dates TEXT NOT NULL DEFAULT '',
                suspended INTEGER NOT NULL DEFAULT 0,
                is_admin INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS care_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                family_id INTEGER NOT NULL REFERENCES users(id),
                caretaker_id INTEGER REFERENCES users(id),
                patient_name TEXT NOT NULL,
                patient_age INTEGER NOT NULL,
                hospital TEXT NOT NULL,
                city TEXT NOT NULL,
                ward_room TEXT NOT NULL,
                care_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                hours INTEGER NOT NULL,
                hourly_rate INTEGER NOT NULL,
                gender_preference TEXT NOT NULL DEFAULT 'Any',
                support_notes TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','accepted','in_progress','completed','cancelled')),
                created_at TEXT NOT NULL,
                accepted_at TEXT,
                start_otp TEXT,
                started_at TEXT,
                actual_minutes INTEGER,
                final_amount INTEGER,
                end_requested INTEGER NOT NULL DEFAULT 0,
                skill_needed TEXT NOT NULL DEFAULT 'General companionship',
                watch_token TEXT,
                completed_at TEXT,
                base_rate INTEGER,
                night_surcharge INTEGER NOT NULL DEFAULT 0,
                urgent_surcharge INTEGER NOT NULL DEFAULT 0,
                weekend_surcharge INTEGER NOT NULL DEFAULT 0,
                skill_surcharge INTEGER NOT NULL DEFAULT 0,
                estimated_amount INTEGER,
                deposit_amount INTEGER NOT NULL DEFAULT 0,
                deposit_status TEXT NOT NULL DEFAULT 'not_paid',
                payment_status TEXT NOT NULL DEFAULT 'not_due',
                payment_reference TEXT
            );
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER NOT NULL REFERENCES care_requests(id) ON DELETE CASCADE,
                rater_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                ratee_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                stars INTEGER NOT NULL CHECK(stars BETWEEN 1 AND 5),
                review TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE(request_id, rater_id)
            );
            CREATE TABLE IF NOT EXISTS watch_viewers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER NOT NULL REFERENCES care_requests(id) ON DELETE CASCADE,
                viewer_key TEXT NOT NULL,
                name TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                UNIQUE(request_id, viewer_key)
            );
            CREATE TABLE IF NOT EXISTS request_cancellations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER NOT NULL REFERENCES care_requests(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_requests_status_city ON care_requests(status, city);
            """
        )
        # Lightweight migrations keep existing local databases compatible.
        user_columns = table_columns(db, "users")
        user_additions = {
            "headline": "TEXT NOT NULL DEFAULT 'Compassionate hospital companion'",
            "experience_years": "INTEGER NOT NULL DEFAULT 1",
            "languages": "TEXT NOT NULL DEFAULT 'Hindi, English'",
            "hourly_rate": "INTEGER NOT NULL DEFAULT 150",
            "skills": "TEXT NOT NULL DEFAULT 'General companionship'",
            "credential_badge": "TEXT NOT NULL DEFAULT 'Companion verified'",
            "credential_verified": "INTEGER NOT NULL DEFAULT 0",
            "rating_count": "INTEGER NOT NULL DEFAULT 0",
            "availability_hours": "TEXT NOT NULL DEFAULT 'Mon–Sun · 08:00–20:00'",
            "preferred_hospitals": "TEXT NOT NULL DEFAULT ''",
            "unavailable_dates": "TEXT NOT NULL DEFAULT ''",
            "suspended": "INTEGER NOT NULL DEFAULT 0",
            "is_admin": "INTEGER NOT NULL DEFAULT 0",
        }
        for name, definition in user_additions.items():
            if name not in user_columns:
                db.execute(f"ALTER TABLE users ADD COLUMN {name} {definition}")
        request_columns = table_columns(db, "care_requests")
        request_additions = {
            "start_otp": "TEXT",
            "started_at": "TEXT",
            "actual_minutes": "INTEGER",
            "final_amount": "INTEGER",
            "end_requested": "INTEGER NOT NULL DEFAULT 0",
            "skill_needed": "TEXT NOT NULL DEFAULT 'General companionship'",
            "watch_token": "TEXT",
            "base_rate": "INTEGER",
            "night_surcharge": "INTEGER NOT NULL DEFAULT 0",
            "urgent_surcharge": "INTEGER NOT NULL DEFAULT 0",
            "weekend_surcharge": "INTEGER NOT NULL DEFAULT 0",
            "skill_surcharge": "INTEGER NOT NULL DEFAULT 0",
            "estimated_amount": "INTEGER",
            "deposit_amount": "INTEGER NOT NULL DEFAULT 0",
            "deposit_status": "TEXT NOT NULL DEFAULT 'not_paid'",
            "payment_status": "TEXT NOT NULL DEFAULT 'not_due'",
            "payment_reference": "TEXT",
        }
        for name, definition in request_additions.items():
            if name not in request_columns:
                db.execute(f"ALTER TABLE care_requests ADD COLUMN {name} {definition}")
        count = db.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
        if count == 0 and DEMO_MODE:
            seed_demo_accounts(db)
        if ADMIN_EMAIL and ADMIN_PASSWORD:
            db.execute("""INSERT INTO users(name,email,phone,password_hash,role,city,verified,is_admin,created_at)
                          VALUES(?,?,?,?, 'family','',1,1,?) ON CONFLICT(email) DO NOTHING""",
                       ("CareSathi Admin", ADMIN_EMAIL, "", password_hash(ADMIN_PASSWORD), utc_now()))
        # Accepted bookings created by older versions receive a start OTP during migration.
        missing_otps = db.execute("SELECT id FROM care_requests WHERE status='accepted' AND start_otp IS NULL").fetchall()
        for request in missing_otps:
            db.execute("UPDATE care_requests SET start_otp=? WHERE id=?", (f"{secrets.randbelow(1_000_000):06d}", request["id"]))


def seed_demo_accounts(db) -> None:
    """Local-only accounts for testing roles; no patient or marketplace records are seeded."""
    created = utc_now()
    people = [
        ("Demo Family", "family@demo.in", "9000000001", "family", "Pune", 1, 0, 0),
        ("Demo Caretaker", "caretaker@demo.in", "9000000002", "caretaker", "Pune", 1, 0, 0),
        ("Demo Admin", "admin@demo.in", "9000000003", "family", "Pune", 1, 0, 0),
    ]
    for name, email, phone, role, city, verified, rating, jobs in people:
        db.execute(
            "INSERT INTO users(name,email,phone,password_hash,role,city,verified,rating,jobs_completed,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (name, email, phone, password_hash("demo123"), role, city, verified, rating, jobs, created),
        )
    db.execute("UPDATE users SET is_admin=1 WHERE email='admin@demo.in'")


def user_dict(row: sqlite3.Row) -> dict:
    return {key: row[key] for key in ("id", "name", "email", "phone", "role", "city", "verified", "rating", "rating_count", "jobs_completed", "skills", "credential_badge", "credential_verified", "availability_hours", "preferred_hospitals", "unavailable_dates", "suspended", "is_admin")}


def request_dict(row: sqlite3.Row, include_otp: bool = False) -> dict:
    data = dict(row)
    if not include_otp:
        data.pop("start_otp", None)
    return data


def pricing_for(care_date: str, start_time: str, hours: int, hourly_rate: int, skill_needed: str, urgent: bool = False) -> dict:
    """Return a transparent, deterministic estimate for the demo checkout."""
    base = hourly_rate * hours
    try:
        is_weekend = datetime.fromisoformat(care_date).weekday() >= 5
    except ValueError:
        is_weekend = False
    is_night = start_time < "06:00" or start_time >= "22:00"
    night = round(base * .20) if is_night else 0
    weekend = round(base * .10) if is_weekend else 0
    skill = round(base * .15) if skill_needed not in ("", "Any", "General companionship") else 0
    urgency = round(base * .15) if urgent else 0
    estimate = base + night + weekend + skill + urgency
    return {"base_rate": base, "night_surcharge": night, "weekend_surcharge": weekend,
            "skill_surcharge": skill, "urgent_surcharge": urgency, "estimated_amount": estimate,
            "deposit_amount": max(50, round(estimate * .20))}


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message


class CareSathiHandler(SimpleHTTPRequestHandler):
    server_version = "CareSathi/1.0"

    def log_message(self, fmt: str, *args) -> None:
        sys.stdout.write(f"[{self.log_date_time_string()}] {fmt % args}\n")

    def send_json(self, data: dict | list, status: int = 200, cookie: str | None = None) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(payload)

    def body_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 50_000:
                raise ApiError(413, "Request is too large")
            return json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            raise ApiError(400, "Invalid JSON")

    def current_user(self, required: bool = True) -> sqlite3.Row | None:
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        token = cookie.get("session")
        if token:
            with connect() as db:
                row = db.execute(
                    """SELECT u.* FROM users u JOIN sessions s ON s.user_id=u.id
                       WHERE s.token=? AND s.expires_at>?""",
                    (token.value, utc_now()),
                ).fetchone()
                if row:
                    return row
        if required:
            raise ApiError(401, "Please sign in to continue")
        return None

    def require_role(self, role: str) -> sqlite3.Row:
        user = self.current_user()
        if user["role"] != role:
            raise ApiError(403, f"This action is only available to {role} accounts")
        return user

    def do_GET(self) -> None:
        try:
            path = urlparse(self.path).path
            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[:2] == ["api", "watch"]:
                return self.handle_watch_get(parts[2])
            if path == "/api/me":
                user = self.current_user(False)
                return self.send_json({"user": user_dict(user) if user else None})
            if path == "/api/health":
                with connect() as db:
                    db.execute("SELECT 1").fetchone()
                return self.send_json({"ok": True, "database": "postgres" if USE_POSTGRES else "sqlite"})
            if path == "/api/config":
                return self.send_json({"demo_mode": DEMO_MODE})
            if path == "/api/requests":
                return self.handle_requests_list()
            if path == "/api/caretakers":
                return self.handle_caretakers_list()
            if path == "/api/availability":
                return self.handle_availability_get()
            if path == "/api/earnings":
                return self.handle_earnings()
            if path == "/api/admin/overview":
                return self.handle_admin_overview()
            if len(parts) == 4 and parts[:2] == ["api", "requests"] and parts[3] == "invoice":
                return self.handle_invoice(int(parts[2]))
            if path == "/api/stats":
                with connect() as db:
                    stats = {
                        "caretakers": db.execute("SELECT COUNT(*) n FROM users WHERE role='caretaker' AND verified=1").fetchone()["n"],
                        "completed": db.execute("SELECT COALESCE(SUM(jobs_completed),0) n FROM users WHERE role='caretaker'").fetchone()["n"],
                        "cities": db.execute("SELECT COUNT(DISTINCT city) n FROM users WHERE role='caretaker'").fetchone()["n"],
                    }
                return self.send_json(stats)
            return self.serve_static(path)
        except ApiError as exc:
            self.send_json({"error": exc.message}, exc.status)
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            self.send_json({"error": "Something went wrong"}, 500)

    def do_POST(self) -> None:
        try:
            path = urlparse(self.path).path
            if path == "/api/register":
                return self.handle_register()
            if path == "/api/login":
                return self.handle_login()
            if path == "/api/logout":
                return self.handle_logout()
            if path == "/api/requests":
                return self.handle_create_request()
            if path == "/api/availability":
                return self.handle_availability_save()
            parts = path.strip("/").split("/")
            if len(parts) == 4 and parts[:2] == ["api", "watch"] and parts[3] == "join":
                return self.handle_watch_join(parts[2])
            if len(parts) == 4 and parts[:2] == ["api", "requests"] and parts[3] in {"accept", "start", "complete", "cancel", "release", "request_end", "rate", "watch_link", "pay_deposit", "settle_payment"}:
                return self.handle_request_action(int(parts[2]), parts[3])
            if len(parts) == 5 and parts[:2] == ["api", "admin"] and parts[2] == "users" and parts[4] in {"approve", "suspend"}:
                return self.handle_admin_user_action(int(parts[3]), parts[4])
            raise ApiError(404, "Not found")
        except ValueError:
            self.send_json({"error": "Invalid request id"}, 400)
        except ApiError as exc:
            self.send_json({"error": exc.message}, exc.status)
        except DB_INTEGRITY_ERRORS:
            self.send_json({"error": "That email is already registered"}, 409)
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            self.send_json({"error": "Something went wrong"}, 500)

    def serve_static(self, path: str) -> None:
        relative = "index.html" if path in ("/", "") else path.lstrip("/")
        target = (PUBLIC_DIR / relative).resolve()
        if PUBLIC_DIR.resolve() not in target.parents and target != PUBLIC_DIR.resolve():
            raise ApiError(403, "Forbidden")
        if not target.is_file():
            target = PUBLIC_DIR / "index.html"
        data = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8" if content_type.startswith("text/") else content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def new_session(self, user_id: int) -> str:
        token = secrets.token_urlsafe(32)
        expires = (datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)).isoformat(timespec="seconds")
        with connect() as db:
            db.execute("DELETE FROM sessions WHERE expires_at < ?", (utc_now(),))
            db.execute("INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)", (token, user_id, expires))
        secure = "; Secure" if os.environ.get("VERCEL") or os.environ.get("CARESATHI_SECURE_COOKIES") == "1" else ""
        return f"session={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={SESSION_HOURS * 3600}{secure}"

    def handle_register(self) -> None:
        data = self.body_json()
        required = ("name", "email", "phone", "password", "role", "city")
        if any(not str(data.get(k, "")).strip() for k in required):
            raise ApiError(400, "Please complete every field")
        if data["role"] not in ("family", "caretaker"):
            raise ApiError(400, "Choose a valid account type")
        if len(data["password"]) < 6:
            raise ApiError(400, "Password must be at least 6 characters")
        with connect() as db:
            user_id = insert_and_get_id(db,
                "INSERT INTO users(name,email,phone,password_hash,role,city,created_at) VALUES(?,?,?,?,?,?,?)",
                (data["name"].strip(), data["email"].strip().lower(), data["phone"].strip(), password_hash(data["password"]), data["role"], data["city"].strip(), utc_now()),
            )
            user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        self.send_json({"user": user_dict(user)}, 201, self.new_session(user["id"]))

    def handle_login(self) -> None:
        data = self.body_json()
        with connect() as db:
            user = db.execute("SELECT * FROM users WHERE email=?", (str(data.get("email", "")).strip().lower(),)).fetchone()
        if not user or not verify_password(str(data.get("password", "")), user["password_hash"]):
            raise ApiError(401, "Email or password is incorrect")
        self.send_json({"user": user_dict(user)}, cookie=self.new_session(user["id"]))

    def handle_logout(self) -> None:
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        if cookie.get("session"):
            with connect() as db:
                db.execute("DELETE FROM sessions WHERE token=?", (cookie["session"].value,))
        self.send_json({"ok": True}, cookie="session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0")

    def handle_requests_list(self) -> None:
        user = self.current_user()
        with connect() as db:
            if user["role"] == "family":
                rows = db.execute(
                    """SELECT r.*, c.name caretaker_name, c.phone caretaker_phone, c.rating caretaker_rating,
                              c.credential_badge caretaker_badge, c.credential_verified caretaker_credential_verified,
                              (SELECT stars FROM ratings WHERE request_id=r.id AND rater_id=?) my_rating,
                              (SELECT rc.reason FROM request_cancellations rc WHERE rc.request_id=r.id ORDER BY rc.id DESC LIMIT 1) last_release_reason,
                              (SELECT u.name FROM request_cancellations rc JOIN users u ON u.id=rc.user_id WHERE rc.request_id=r.id ORDER BY rc.id DESC LIMIT 1) last_released_by
                       FROM care_requests r LEFT JOIN users c ON c.id=r.caretaker_id
                       WHERE r.family_id=? ORDER BY r.created_at DESC""", (user["id"], user["id"])
                ).fetchall()
            else:
                rows = db.execute(
                    """SELECT r.*, f.name family_name, f.rating family_rating, f.rating_count family_rating_count,
                              c.name caretaker_name,
                              (SELECT stars FROM ratings WHERE request_id=r.id AND rater_id=?) my_rating,
                              (SELECT rc.reason FROM request_cancellations rc WHERE rc.request_id=r.id ORDER BY rc.id DESC LIMIT 1) last_release_reason,
                              (SELECT u.name FROM request_cancellations rc JOIN users u ON u.id=rc.user_id WHERE rc.request_id=r.id ORDER BY rc.id DESC LIMIT 1) last_released_by
                       FROM care_requests r JOIN users f ON f.id=r.family_id LEFT JOIN users c ON c.id=r.caretaker_id
                       WHERE r.status='open' OR r.caretaker_id=?
                       ORDER BY CASE r.status WHEN 'in_progress' THEN 0 WHEN 'accepted' THEN 1 WHEN 'open' THEN 2 ELSE 3 END, r.created_at DESC""",
                    (user["id"], user["id"]),
                ).fetchall()
                rows = [row for row in rows if row["caretaker_id"] == user["id"] or cities_match(user["city"], row["city"])]
        self.send_json([request_dict(row, include_otp=user["role"] == "family") for row in rows])

    def handle_caretakers_list(self) -> None:
        user = self.require_role("family")
        with connect() as db:
            rows = db.execute(
                """SELECT id,name,city,verified,rating,rating_count,jobs_completed,headline,experience_years,languages,hourly_rate,
                          skills,credential_badge,credential_verified,availability_hours,preferred_hospitals,unavailable_dates
                   FROM users WHERE role='caretaker' AND suspended=0
                   ORDER BY verified DESC, rating DESC, jobs_completed DESC""",
            ).fetchall()
        ordered = sorted(rows, key=lambda row: (not cities_match(user["city"], row["city"]), -row["verified"], -row["rating"], -row["jobs_completed"]))
        payload = []
        for row in ordered:
            item = dict(row)
            item["nearby"] = cities_match(user["city"], row["city"])
            payload.append(item)
        self.send_json(payload)

    def handle_availability_get(self) -> None:
        user = self.require_role("caretaker")
        self.send_json({"availability_hours": user["availability_hours"], "preferred_hospitals": user["preferred_hospitals"],
                        "unavailable_dates": user["unavailable_dates"]})

    def handle_availability_save(self) -> None:
        user = self.require_role("caretaker")
        data = self.body_json()
        hours = str(data.get("availability_hours", "")).strip()[:120]
        hospitals = str(data.get("preferred_hospitals", "")).strip()[:500]
        dates = str(data.get("unavailable_dates", "")).strip()[:500]
        if not hours:
            raise ApiError(400, "Please add your usual working hours")
        with connect() as db:
            db.execute("UPDATE users SET availability_hours=?, preferred_hospitals=?, unavailable_dates=? WHERE id=?",
                       (hours, hospitals, dates, user["id"]))
            updated = db.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        self.send_json({"user": user_dict(updated)})

    def handle_earnings(self) -> None:
        user = self.require_role("caretaker")
        with connect() as db:
            rows = db.execute("""SELECT id,patient_name,hospital,care_date,completed_at,actual_minutes,final_amount,payment_status,
                                      (SELECT stars FROM ratings WHERE request_id=care_requests.id AND ratee_id=?) rating
                               FROM care_requests WHERE caretaker_id=? AND status='completed' ORDER BY completed_at DESC""",
                              (user["id"], user["id"])).fetchall()
        total = sum(int(row["final_amount"] or 0) for row in rows)
        pending = sum(int(row["final_amount"] or 0) for row in rows if row["payment_status"] != "paid")
        week_cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(timespec="seconds")
        weekly = sum(int(row["final_amount"] or 0) for row in rows if (row["completed_at"] or "") >= week_cutoff)
        self.send_json({"total_earned": total, "weekly_earned": weekly, "pending_payout": pending,
                        "completed_shifts": len(rows), "items": [dict(row) for row in rows]})

    def handle_invoice(self, request_id: int) -> None:
        user = self.current_user()
        with connect() as db:
            row = db.execute("""SELECT r.*,f.name family_name,f.email family_email,c.name caretaker_name
                                FROM care_requests r JOIN users f ON f.id=r.family_id LEFT JOIN users c ON c.id=r.caretaker_id WHERE r.id=?""", (request_id,)).fetchone()
        if not row or user["id"] not in (row["family_id"], row["caretaker_id"]) and not user["is_admin"]:
            raise ApiError(403, "You cannot access this invoice")
        total = row["final_amount"] or row["estimated_amount"] or row["hourly_rate"] * row["hours"]
        self.send_json({"invoice_no": f"CS-{row['id']:05d}", "issued_at": row["completed_at"] or row["created_at"],
                        "patient_name": row["patient_name"], "hospital": row["hospital"], "care_date": row["care_date"],
                        "family_name": row["family_name"], "caretaker_name": row["caretaker_name"] or "Pending assignment",
                        "base_rate": row["base_rate"] or row["hourly_rate"] * row["hours"], "night_surcharge": row["night_surcharge"],
                        "weekend_surcharge": row["weekend_surcharge"], "skill_surcharge": row["skill_surcharge"], "urgent_surcharge": row["urgent_surcharge"],
                        "deposit_amount": row["deposit_amount"], "total": total, "payment_status": row["payment_status"]})

    def handle_admin_overview(self) -> None:
        admin = self.current_user()
        if not admin["is_admin"]:
            raise ApiError(403, "Admin access is required")
        with connect() as db:
            users = db.execute("SELECT id,name,email,role,city,verified,suspended,rating,jobs_completed,created_at FROM users WHERE is_admin=0 ORDER BY created_at DESC").fetchall()
            requests = db.execute("SELECT status,COUNT(*) total FROM care_requests GROUP BY status").fetchall()
            ratings = db.execute("SELECT COUNT(*) total,COALESCE(AVG(stars),0) average FROM ratings").fetchone()
            payments = db.execute("SELECT COALESCE(SUM(final_amount),0) paid_volume, COUNT(*) completed FROM care_requests WHERE status='completed'").fetchone()
        self.send_json({"users": [dict(row) for row in users], "request_statuses": {row["status"]:row["total"] for row in requests},
                        "ratings": dict(ratings), "payments": dict(payments)})

    def handle_admin_user_action(self, user_id: int, action: str) -> None:
        admin = self.current_user()
        if not admin["is_admin"]:
            raise ApiError(403, "Admin access is required")
        with connect() as db:
            target = db.execute("SELECT * FROM users WHERE id=? AND is_admin=0", (user_id,)).fetchone()
            if not target:
                raise ApiError(404, "User not found")
            if action == "approve":
                db.execute("UPDATE users SET verified=1 WHERE id=?", (user_id,))
            else:
                db.execute("UPDATE users SET suspended=CASE suspended WHEN 1 THEN 0 ELSE 1 END WHERE id=?", (user_id,))
            target = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        self.send_json({"user": user_dict(target)})

    def handle_create_request(self) -> None:
        user = self.require_role("family")
        data = self.body_json()
        required = ("patient_name", "patient_age", "hospital", "city", "ward_room", "care_date", "start_time", "hours", "hourly_rate")
        if any(str(data.get(k, "")).strip() == "" for k in required):
            raise ApiError(400, "Please complete all required care details")
        try:
            age, hours, rate = int(data["patient_age"]), int(data["hours"]), int(data["hourly_rate"])
        except (ValueError, TypeError):
            raise ApiError(400, "Age, hours, and rate must be numbers")
        if not (1 <= age <= 120 and 1 <= hours <= 24 and 50 <= rate <= 5000):
            raise ApiError(400, "Please check age, duration, and hourly rate")
        pricing = pricing_for(data["care_date"], data["start_time"], hours, rate, data.get("skill_needed", "General companionship"), bool(data.get("urgent")))
        with connect() as db:
            request_id = insert_and_get_id(db,
                """INSERT INTO care_requests(family_id,patient_name,patient_age,hospital,city,ward_room,care_date,start_time,hours,hourly_rate,gender_preference,support_notes,status,created_at,base_rate,night_surcharge,weekend_surcharge,skill_surcharge,urgent_surcharge,estimated_amount,deposit_amount)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?, 'open', ?,?,?,?,?,?,?,?)""",
                (user["id"], data["patient_name"].strip(), age, data["hospital"].strip(), data["city"].strip(), data["ward_room"].strip(), data["care_date"], data["start_time"], hours, rate, data.get("gender_preference", "Any"), data.get("support_notes", "").strip(), utc_now(), pricing["base_rate"], pricing["night_surcharge"], pricing["weekend_surcharge"], pricing["skill_surcharge"], pricing["urgent_surcharge"], pricing["estimated_amount"], pricing["deposit_amount"]),
            )
            db.execute("UPDATE care_requests SET skill_needed=? WHERE id=?", (data.get("skill_needed", "General companionship"), request_id))
            row = db.execute("SELECT * FROM care_requests WHERE id=?", (request_id,)).fetchone()
        self.send_json(request_dict(row, include_otp=True), 201)

    def handle_request_action(self, request_id: int, action: str) -> None:
        user = self.current_user()
        with connect() as db:
            request = db.execute("SELECT * FROM care_requests WHERE id=?", (request_id,)).fetchone()
            if not request:
                raise ApiError(404, "Care request not found")
            if action == "rate":
                if request["status"] != "completed" or user["id"] not in (request["family_id"], request["caretaker_id"]):
                    raise ApiError(403, "Ratings are available to both participants after a completed shift")
                data = self.body_json()
                try:
                    stars = int(data.get("stars", 0))
                except (TypeError, ValueError):
                    stars = 0
                if stars not in range(1, 6):
                    raise ApiError(400, "Choose a rating from 1 to 5 stars")
                ratee_id = request["caretaker_id"] if user["id"] == request["family_id"] else request["family_id"]
                try:
                    db.execute(
                        "INSERT INTO ratings(request_id,rater_id,ratee_id,stars,review,created_at) VALUES(?,?,?,?,?,?)",
                        (request_id, user["id"], ratee_id, stars, str(data.get("review", "")).strip()[:500], utc_now()),
                    )
                except DB_INTEGRITY_ERRORS:
                    raise ApiError(409, "You have already rated this shift")
                aggregate = db.execute("SELECT AVG(stars) average, COUNT(*) total FROM ratings WHERE ratee_id=?", (ratee_id,)).fetchone()
                db.execute("UPDATE users SET rating=?, rating_count=? WHERE id=?", (round(aggregate["average"], 1), aggregate["total"], ratee_id))
            elif action == "watch_link":
                if request["family_id"] != user["id"]:
                    raise ApiError(403, "Only the patient's family can create a watch link")
                token = request["watch_token"] or secrets.token_urlsafe(24)
                db.execute("UPDATE care_requests SET watch_token=? WHERE id=?", (token, request_id))
            elif action == "accept":
                if user["role"] != "caretaker" or user["suspended"] or request["status"] != "open":
                    raise ApiError(409, "This request is no longer available")
                otp = f"{secrets.randbelow(1_000_000):06d}"
                result = db.execute(
                    "UPDATE care_requests SET status='accepted', caretaker_id=?, accepted_at=?, start_otp=? WHERE id=? AND status='open'",
                    (user["id"], utc_now(), otp, request_id),
                )
                if result.rowcount != 1:
                    raise ApiError(409, "Another caretaker just accepted this request")
            elif action == "start":
                if request["caretaker_id"] != user["id"] or request["status"] != "accepted":
                    raise ApiError(403, "You cannot start this assignment")
                data = self.body_json()
                supplied_otp = str(data.get("otp", "")).strip()
                if not request["start_otp"] or not hmac.compare_digest(supplied_otp, request["start_otp"]):
                    raise ApiError(400, "The start OTP is incorrect")
                db.execute("UPDATE care_requests SET status='in_progress', started_at=? WHERE id=?", (utc_now(), request_id))
            elif action == "complete":
                if request["caretaker_id"] != user["id"] or request["status"] != "in_progress":
                    raise ApiError(403, "You cannot complete this assignment")
                completed_at = datetime.now(timezone.utc)
                started_at = datetime.fromisoformat(request["started_at"])
                elapsed_seconds = max(1, int((completed_at - started_at).total_seconds()))
                actual_minutes = max(1, (elapsed_seconds + 59) // 60)
                base_for_time = max(1, round(request["hourly_rate"] * actual_minutes / 60))
                booked_base = request["base_rate"] or request["hourly_rate"] * request["hours"]
                ratio = base_for_time / booked_base
                extras = sum(int(request[key] or 0) for key in ("night_surcharge", "weekend_surcharge", "skill_surcharge", "urgent_surcharge"))
                final_amount = base_for_time + round(extras * ratio)
                db.execute(
                    "UPDATE care_requests SET status='completed', completed_at=?, actual_minutes=?, final_amount=?, payment_status=CASE WHEN deposit_status='paid' THEN 'balance_due' ELSE 'payment_due' END WHERE id=?",
                    (completed_at.isoformat(timespec="seconds"), actual_minutes, final_amount, request_id),
                )
                db.execute("UPDATE users SET jobs_completed=jobs_completed+1 WHERE id=?", (user["id"],))
            elif action == "cancel":
                if request["family_id"] != user["id"] or request["status"] not in ("open", "accepted"):
                    raise ApiError(403, "This request cannot be cancelled")
                payment_status = "refunded" if request["deposit_status"] == "paid" else "cancelled"
                db.execute("UPDATE care_requests SET status='cancelled', payment_status=? WHERE id=?", (payment_status, request_id))
            elif action == "pay_deposit":
                if request["family_id"] != user["id"] or request["status"] not in ("open", "accepted"):
                    raise ApiError(403, "A deposit can only be paid by the patient's family before the shift")
                if request["deposit_status"] == "paid":
                    raise ApiError(409, "The booking deposit is already paid")
                ref = f"DEMO-DEP-{request_id}-{secrets.randbelow(9000)+1000}"
                db.execute("UPDATE care_requests SET deposit_status='paid', payment_status='deposit_paid', payment_reference=? WHERE id=?", (ref, request_id))
            elif action == "settle_payment":
                if request["family_id"] != user["id"] or request["status"] != "completed":
                    raise ApiError(403, "Only the patient's family can settle a completed shift")
                if request["payment_status"] == "paid":
                    raise ApiError(409, "This shift has already been paid")
                ref = request["payment_reference"] or f"DEMO-PAY-{request_id}-{secrets.randbelow(9000)+1000}"
                db.execute("UPDATE care_requests SET payment_status='paid', payment_reference=? WHERE id=?", (ref, request_id))
            elif action == "release":
                if request["caretaker_id"] != user["id"] or request["status"] != "accepted":
                    raise ApiError(403, "Only the assigned CareSathi can release a shift before it starts")
                data = self.body_json()
                reason = str(data.get("reason", "")).strip()
                if len(reason) < 5:
                    raise ApiError(400, "Please provide a clear cancellation reason")
                db.execute(
                    "INSERT INTO request_cancellations(request_id,user_id,reason,created_at) VALUES(?,?,?,?)",
                    (request_id, user["id"], reason[:500], utc_now()),
                )
                db.execute(
                    """UPDATE care_requests SET status='open',caretaker_id=NULL,accepted_at=NULL,start_otp=NULL,
                       started_at=NULL,end_requested=0 WHERE id=? AND status='accepted' AND caretaker_id=?""",
                    (request_id, user["id"]),
                )
            elif action == "request_end":
                if request["family_id"] != user["id"] or request["status"] != "in_progress":
                    raise ApiError(403, "Only the family can request an early end during an active shift")
                db.execute("UPDATE care_requests SET end_requested=1 WHERE id=?", (request_id,))
            updated = db.execute("SELECT * FROM care_requests WHERE id=?", (request_id,)).fetchone()
        payload = request_dict(updated, include_otp=user["role"] == "family")
        if action == "watch_link":
            payload = {"token": updated["watch_token"]}
        self.send_json(payload)

    def handle_watch_get(self, token: str) -> None:
        with connect() as db:
            request = db.execute(
                """SELECT r.id,r.patient_name,r.hospital,r.city,r.ward_room,r.status,r.started_at,r.care_date,r.start_time,
                          r.skill_needed,c.name caretaker_name,c.rating caretaker_rating,c.credential_badge caretaker_badge,
                          c.credential_verified caretaker_credential_verified
                   FROM care_requests r LEFT JOIN users c ON c.id=r.caretaker_id WHERE r.watch_token=?""",
                (token,),
            ).fetchone()
            if not request:
                raise ApiError(404, "This private watch link is invalid or has expired")
            cutoff = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat(timespec="seconds")
            viewers = db.execute(
                "SELECT name,last_seen FROM watch_viewers WHERE request_id=? AND last_seen>? ORDER BY last_seen DESC",
                (request["id"], cutoff),
            ).fetchall()
        payload = dict(request)
        payload["viewers"] = [dict(viewer) for viewer in viewers]
        payload["emergency_numbers"] = [{"label": "National emergency", "number": "112"}, {"label": "Ambulance", "number": "108"}]
        self.send_json(payload)

    def handle_watch_join(self, token: str) -> None:
        data = self.body_json()
        name = str(data.get("name", "Family member")).strip()[:50] or "Family member"
        viewer_key = str(data.get("viewer_key", "")).strip() or secrets.token_urlsafe(12)
        with connect() as db:
            request = db.execute("SELECT id FROM care_requests WHERE watch_token=?", (token,)).fetchone()
            if not request:
                raise ApiError(404, "This private watch link is invalid or has expired")
            db.execute(
                """INSERT INTO watch_viewers(request_id,viewer_key,name,last_seen) VALUES(?,?,?,?)
                   ON CONFLICT(request_id,viewer_key) DO UPDATE SET name=excluded.name,last_seen=excluded.last_seen""",
                (request["id"], viewer_key, name, utc_now()),
            )
        self.send_json({"viewer_key": viewer_key, "ok": True})


def run(port: int = 8000) -> None:
    init_db()
    server = ThreadingHTTPServer(("127.0.0.1", port), CareSathiHandler)
    print(f"CareSathi is running at http://localhost:{port}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping CareSathi…")
    finally:
        server.server_close()


if __name__ == "__main__":
    run(int(os.environ.get("PORT", "8000")))
