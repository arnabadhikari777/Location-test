import os
import secrets
import sqlite3
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session, redirect, url_for, flash

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-secret-key")

API_KEY = os.getenv("OPENWEATHER_API_KEY")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", Path(__file__).with_name("weather.db")))


def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visitor_id TEXT NOT NULL UNIQUE,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            session_started TEXT NOT NULL,
            total_active_seconds REAL NOT NULL DEFAULT 0,
            last_latitude REAL,
            last_longitude REAL,
            last_accuracy REAL,
            location_updated_at TEXT,
            location_updates INTEGER NOT NULL DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_visitors_last_seen ON visitors(last_seen);
        CREATE INDEX IF NOT EXISTS idx_visitors_location ON visitors(last_latitude, last_longitude);
        """)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def get_or_create_visitor():
    visitor_id = request.cookies.get("weather_visitor_id")
    if not visitor_id:
        visitor_id = secrets.token_urlsafe(24)

    now = now_iso()
    with get_db() as db:
        visitor = db.execute(
            "SELECT * FROM visitors WHERE visitor_id = ?", (visitor_id,)
        ).fetchone()
        if visitor is None:
            db.execute(
                """INSERT INTO visitors
                   (visitor_id, first_seen, last_seen, session_started)
                   VALUES (?, ?, ?, ?)""",
                (visitor_id, now, now, now),
            )
        else:
            db.execute(
                "UPDATE visitors SET last_seen = ? WHERE visitor_id = ?",
                (now, visitor_id),
            )
    return visitor_id


def set_visitor_cookie(response, visitor_id):
    if not request.cookies.get("weather_visitor_id"):
        response.set_cookie(
            "weather_visitor_id",
            visitor_id,
            max_age=60 * 60 * 24 * 365,
            httponly=True,
            samesite="Lax",
            secure=request.is_secure,
        )
    return response


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/", methods=["GET", "POST"])
def home():
    visitor_id = get_or_create_visitor()
    weather = None
    error = None

    if request.method == "POST":
        city = request.form.get("city", "").strip()

        if not city:
            error = "Please enter a city name."
        elif not API_KEY:
            error = "API key is missing. Please check your .env file."
        else:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {"q": city, "appid": API_KEY, "units": "metric"}
            try:
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    weather = {
                        "city": data["name"],
                        "country": data["sys"]["country"],
                        "temperature": round(data["main"]["temp"]),
                        "description": data["weather"][0]["description"],
                        "humidity": data["main"]["humidity"],
                        "wind_speed": data["wind"]["speed"],
                        "icon": data["weather"][0]["icon"],
                    }
                elif response.status_code == 404:
                    error = "City not found. Please check the city name."
                elif response.status_code == 401:
                    error = "Invalid API key. Please check your API key."
                else:
                    error = "Unable to get weather data. Please try again."
            except requests.exceptions.RequestException:
                error = "Network error. Please check your internet connection."

    response = render_template("home.html", weather=weather, error=error)
    rendered = app.make_response(response)
    return set_visitor_cookie(rendered, visitor_id)


@app.post("/api/location")
def update_location():
    visitor_id = request.cookies.get("weather_visitor_id")
    if not visitor_id:
        visitor_id = get_or_create_visitor()

    data = request.get_json(silent=True) or {}
    try:
        latitude = float(data["latitude"])
        longitude = float(data["longitude"])
        accuracy = float(data.get("accuracy")) if data.get("accuracy") is not None else None
    except (KeyError, TypeError, ValueError):
        return jsonify({"ok": False, "error": "Invalid location data."}), 400

    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return jsonify({"ok": False, "error": "Location is out of range."}), 400

    now = now_iso()
    with get_db() as db:
        db.execute(
            """UPDATE visitors
               SET last_seen = ?, last_latitude = ?, last_longitude = ?,
                   last_accuracy = ?, location_updated_at = ?,
                   location_updates = location_updates + 1
               WHERE visitor_id = ?""",
            (now, latitude, longitude, accuracy, now, visitor_id),
        )

    response = jsonify({"ok": True})
    return set_visitor_cookie(response, visitor_id)


@app.post("/api/heartbeat")
def heartbeat():
    visitor_id = request.cookies.get("weather_visitor_id")
    if not visitor_id:
        visitor_id = get_or_create_visitor()

    now = now_iso()
    data = request.get_json(silent=True) or {}
    try:
        active_seconds = max(0, min(float(data.get("active_seconds", 0)), 60))
    except (TypeError, ValueError):
        active_seconds = 0

    with get_db() as db:
        db.execute(
            """UPDATE visitors
               SET last_seen = ?, total_active_seconds = total_active_seconds + ?
               WHERE visitor_id = ?""",
            (now, active_seconds, visitor_id),
        )

    response = jsonify({"ok": True})
    return set_visitor_cookie(response, visitor_id)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if ADMIN_PASSWORD and secrets.compare_digest(username, ADMIN_USERNAME) and secrets.compare_digest(password, ADMIN_PASSWORD):
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        flash("Invalid admin credentials.")
    return render_template("admin_login.html")


@app.post("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.get("/admin")
@admin_required
def admin_dashboard():
    with get_db() as db:
        visitors = db.execute("SELECT * FROM visitors ORDER BY last_seen DESC").fetchall()
        total_visitors = db.execute("SELECT COUNT(*) FROM visitors").fetchone()[0]
        located_visitors = db.execute(
            "SELECT COUNT(*) FROM visitors WHERE last_latitude IS NOT NULL"
        ).fetchone()[0]
        total_updates = db.execute("SELECT COALESCE(SUM(location_updates), 0) FROM visitors").fetchone()[0]
        total_active = db.execute("SELECT COALESCE(SUM(total_active_seconds), 0) FROM visitors").fetchone()[0]

    return render_template(
        "admin.html",
        visitors=visitors,
        total_visitors=total_visitors,
        located_visitors=located_visitors,
        total_updates=total_updates,
        total_active=total_active,
    )


@app.post("/admin/delete/<int:visitor_db_id>")
@admin_required
def delete_visitor(visitor_db_id):
    with get_db() as db:
        db.execute("DELETE FROM visitors WHERE id = ?", (visitor_db_id,))
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/delete-all")
@admin_required
def delete_all_visitors():
    with get_db() as db:
        db.execute("DELETE FROM visitors")
    return redirect(url_for("admin_dashboard"))


init_db()

if __name__ == "__main__":
    app.run(debug=True)
