import os
import sqlite3
from functools import wraps

from dotenv import load_dotenv
from flask import (Flask, g, jsonify, redirect, render_template,
                   request, session, url_for)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# absolute path, so it also works on PythonAnywhere's WSGI
load_dotenv(os.path.join(BASE_DIR, ".env"))

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]
ADMIN_USER = os.environ["ADMIN_USER"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]
DB_PATH = os.environ.get("DATABASE_PATH") or os.path.join(BASE_DIR, "locations.db")
if not os.path.isabs(DB_PATH):
    DB_PATH = os.path.join(BASE_DIR, DB_PATH)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                accuracy REAL,
                ip TEXT,
                user_agent TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/api/location", methods=["POST"])
def save_location():
    data = request.get_json(silent=True) or {}
    try:
        lat = float(data["latitude"])
        lng = float(data["longitude"])
        acc = float(data["accuracy"]) if data.get("accuracy") is not None else None
    except (KeyError, TypeError, ValueError):
        return jsonify(error="invalid data"), 400
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return jsonify(error="out of range"), 400

    db = get_db()
    db.execute(
        "INSERT INTO locations (latitude, longitude, accuracy, ip, user_agent) "
        "VALUES (?, ?, ?, ?, ?)",
        (lat, lng, acc, request.remote_addr,
         request.headers.get("User-Agent", "")[:300]),
    )
    db.commit()
    return jsonify(ok=True)


@app.route("/admin/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if (request.form.get("username") == ADMIN_USER
                and request.form.get("password") == ADMIN_PASSWORD):
            session["is_admin"] = True
            return redirect(url_for("admin"))
        error = "ইউজারনেম বা পাসওয়ার্ড ভুল"
    return render_template("login.html", error=error)


@app.route("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/admin")
@admin_required
def admin():
    rows = get_db().execute(
        "SELECT * FROM locations ORDER BY id DESC").fetchall()
    points = [[r["latitude"], r["longitude"]] for r in rows]
    return render_template("admin.html", rows=rows, points=points)


@app.route("/admin/delete/<int:loc_id>", methods=["POST"])
@admin_required
def delete(loc_id):
    db = get_db()
    db.execute("DELETE FROM locations WHERE id = ?", (loc_id,))
    db.commit()
    return redirect(url_for("admin"))


init_db()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")
