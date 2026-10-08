"""My Weather App - Flask + OpenWeatherMap.

* Weather for the visitor's own location (browser permission) or a searched city
* Admin panel with every visitor's live location
* All secrets (API key, passwords) come from the .env file - never from the code
"""
import hmac
import math
import os
import re
import secrets
import sqlite3
import threading
import time
from collections import deque
from contextlib import closing
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.exceptions import HTTPException, InternalServerError

BASE_DIR = Path(__file__).resolve().parent
# Explicit path: on PythonAnywhere the working directory is NOT the project folder.
load_dotenv(BASE_DIR / ".env")


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
def env_int(name, default):
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


DEBUG = os.getenv("FLASK_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}
API_KEY = os.getenv("OPENWEATHER_API_KEY", "").strip()
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin").strip() or "admin"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
DATABASE_PATH = Path(os.getenv("DATABASE_PATH") or BASE_DIR / "weather.db")
RETENTION_DAYS = env_int("VISITOR_RETENTION_DAYS", 30)  # 0 = keep forever
DISPLAY_TZ = os.getenv("DISPLAY_TIMEZONE", "Asia/Kolkata")

# Values copied straight from .env.example must never count as real secrets.
PLACEHOLDERS = {
    "",
    "change-this-secret-key",
    "replace_with_a_long_random_secret",
    "replace_with_a_strong_admin_password",
    "your_openweathermap_api_key",
}

SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "").strip()
if SECRET_KEY in PLACEHOLDERS or len(SECRET_KEY) < 16:
    if not DEBUG:
        # Refusing to start is safer than silently using a guessable key:
        # anyone who knows the key can forge an admin session cookie.
        raise RuntimeError(
            "FLASK_SECRET_KEY is missing or too short. Put a long random value in .env: "
            'python -c "import secrets; print(secrets.token_hex(32))"'
        )
    SECRET_KEY = secrets.token_hex(32)  # local development only

API_KEY_OK = API_KEY not in PLACEHOLDERS
ADMIN_ENABLED = ADMIN_PASSWORD not in PLACEHOLDERS

try:
    from zoneinfo import ZoneInfo

    LOCAL_TZ = ZoneInfo(DISPLAY_TZ)
except Exception:  # unknown zone name or no tz database on this machine
    LOCAL_TZ = timezone.utc

app = Flask(__name__)
app.config.update(
    SECRET_KEY=SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",  # cross-site POSTs can't carry the admin cookie
    SESSION_COOKIE_SECURE=not DEBUG,  # production runs on HTTPS
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    MAX_CONTENT_LENGTH=16 * 1024,
)

if not API_KEY_OK:
    app.logger.warning("OPENWEATHER_API_KEY is not set - weather lookups are disabled.")
if not ADMIN_ENABLED:
    app.logger.warning("ADMIN_PASSWORD is not set - admin login is disabled.")
elif len(ADMIN_PASSWORD) < 10:
    app.logger.warning("ADMIN_PASSWORD is short - use at least 10 characters.")

CSP = (
    "default-src 'self'; img-src 'self' https://openweathermap.org data:; "
    "style-src 'self'; script-src 'self'; connect-src 'self'; "
    "base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def utcnow():
    return datetime.now(timezone.utc)


def iso(moment):
    return moment.isoformat(timespec="seconds")


def parse_iso(value):
    try:
        moment = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def fmt_local(value):
    moment = parse_iso(value)
    if moment is None:
        return "—"
    return moment.astimezone(LOCAL_TZ).strftime("%d %b %Y, %I:%M:%S %p")


def fmt_ago(seconds):
    if seconds is None:
        return "—"
    seconds = max(0, int(seconds))
    if seconds < 5:
        return "এইমাত্র"
    if seconds < 60:
        return f"{seconds} সেকেন্ড আগে"
    if seconds < 3600:
        return f"{seconds // 60} মিনিট আগে"
    if seconds < 86400:
        return f"{seconds // 3600} ঘণ্টা আগে"
    return f"{seconds // 86400} দিন আগে"


def fmt_duration(seconds):
    seconds = int(seconds or 0)
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def parse_float(value, low, high):
    """float within [low, high] or None (rejects NaN/inf/bool/garbage)."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and low <= number <= high else None


def clean_place(value):
    """Visitor-supplied area label: plain text, one line, max 80 chars."""
    if not isinstance(value, str):
        return None
    value = re.sub(r"[\x00-\x1f\x7f]+", " ", value)
    return " ".join(value.split())[:80] or None


def same(a, b):
    # Bytes, not str: compare_digest raises TypeError on non-ASCII str,
    # which used to turn a Bengali/emoji password attempt into a 500 error.
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def client_ip():
    # Behind PythonAnywhere's proxy the real address is in X-Real-IP / X-Forwarded-For.
    real = request.headers.get("X-Real-IP", "").strip()
    if real:
        return real[:64]
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[-1].strip()[:64]
    return request.remote_addr or "unknown"


# --------------------------------------------------------------------------
# Tiny in-memory sliding-window limiter (per process)
# --------------------------------------------------------------------------
_hits = {}
_hits_lock = threading.Lock()


def count_hits(bucket, key, window):
    now = time.monotonic()
    with _hits_lock:
        queue = _hits.get((bucket, key))
        if not queue:
            return 0
        while queue and now - queue[0] > window:
            queue.popleft()
        return len(queue)


def add_hit(bucket, key):
    now = time.monotonic()
    with _hits_lock:
        _hits.setdefault((bucket, key), deque()).append(now)
        if len(_hits) > 5000:  # tidy up old keys
            for stale in [k for k, q in _hits.items() if not q or now - q[-1] > 3600]:
                del _hits[stale]


def rate_limited(bucket, key, limit, window):
    """True when blocked; otherwise records this hit."""
    if count_hits(bucket, key, window) >= limit:
        return True
    add_hit(bucket, key)
    return False


# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------
# `session_started` is no longer used but stays NOT NULL in databases created by the
# old version, so every INSERT keeps filling it in.
SCHEMA = """
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
    location_updates INTEGER NOT NULL DEFAULT 0,
    place_name TEXT
);
CREATE INDEX IF NOT EXISTS idx_visitors_last_seen ON visitors(last_seen);
"""


def init_db():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DATABASE_PATH, timeout=10)) as db:
        db.executescript(SCHEMA)
        columns = {row[1] for row in db.execute("PRAGMA table_info(visitors)")}
        if "place_name" not in columns:  # database created by the old version
            try:
                db.execute("ALTER TABLE visitors ADD COLUMN place_name TEXT")
                db.commit()
            except sqlite3.OperationalError:  # another worker added it first
                pass


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_PATH, timeout=10)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# --------------------------------------------------------------------------
# Visitors
# --------------------------------------------------------------------------
VISITOR_COOKIE = "weather_visitor_id"
VISITOR_ID_RE = re.compile(r"^[A-Za-z0-9_-]{20,64}$")
MAX_BEAT_SECONDS = 20  # most active time one heartbeat can add
ONLINE_SECONDS = 45  # seen within this many seconds = "online"
_last_purge = float("-inf")


def visitor_from_request():
    """(visitor_id, is_new). A missing/garbled cookie gets a fresh random id."""
    visitor_id = request.cookies.get(VISITOR_COOKIE, "")
    if VISITOR_ID_RE.match(visitor_id):
        return visitor_id, False
    return secrets.token_urlsafe(24), True


def with_visitor_cookie(response, visitor_id, is_new):
    if is_new:
        response.set_cookie(
            VISITOR_COOKIE,
            visitor_id,
            max_age=60 * 60 * 24 * (RETENTION_DAYS if RETENTION_DAYS > 0 else 365),
            httponly=True,
            samesite="Lax",
            secure=not DEBUG,
        )
    return response


def maybe_purge(db):
    """Delete visitors inactive for RETENTION_DAYS (checked at most once an hour)."""
    global _last_purge
    if RETENTION_DAYS <= 0 or time.monotonic() - _last_purge < 3600:
        return
    _last_purge = time.monotonic()
    cutoff = iso(utcnow() - timedelta(days=RETENTION_DAYS))
    db.execute("DELETE FROM visitors WHERE last_seen < ?", (cutoff,))


def record_visit(visitor_id, coords=None, place=None, claimed_seconds=0.0):
    """Create-or-update the visitor row (so a deleted visitor reappears on its next ping)."""
    db = get_db()
    maybe_purge(db)
    now = utcnow().replace(microsecond=0)  # same precision as the stored timestamps
    stamp = iso(now)
    db.execute(
        "INSERT OR IGNORE INTO visitors (visitor_id, first_seen, last_seen, session_started) "
        "VALUES (?, ?, ?, ?)",
        (visitor_id, stamp, stamp, stamp),
    )
    row = db.execute(
        "SELECT last_seen FROM visitors WHERE visitor_id = ?", (visitor_id,)
    ).fetchone()
    previous = parse_iso(row["last_seen"]) if row else None
    elapsed = max(0.0, (now - previous).total_seconds()) if previous else 0.0
    # Never credit more time than really passed, whatever the browser claims.
    credited = max(0.0, min(claimed_seconds, elapsed + 1, MAX_BEAT_SECONDS))

    sets, args = ["last_seen = ?"], [stamp]
    if credited:
        sets.append("total_active_seconds = total_active_seconds + ?")
        args.append(credited)
    if coords:
        latitude, longitude, accuracy = coords
        sets += [
            "last_latitude = ?",
            "last_longitude = ?",
            "last_accuracy = ?",
            "location_updated_at = ?",
            "location_updates = location_updates + 1",
        ]
        args += [latitude, longitude, accuracy, stamp]
        if place:
            sets.append("place_name = ?")
            args.append(place)
    args.append(visitor_id)
    db.execute(f"UPDATE visitors SET {', '.join(sets)} WHERE visitor_id = ?", args)
    db.commit()


# --------------------------------------------------------------------------
# Weather (OpenWeatherMap)
# --------------------------------------------------------------------------
OWM_URL = "https://api.openweathermap.org/data/2.5/weather"
CACHE_TTL = 600  # seconds
UPSTREAM_PER_MINUTE = 50  # stay below OpenWeatherMap's free-plan limit (60/min)
ICON_RE = re.compile(r"^\d{2}[dn]$")
_cache = {}
_cache_lock = threading.Lock()


class WeatherError(Exception):
    def __init__(self, message, status):
        super().__init__(message)
        self.message = message
        self.status = status


def condition_bn(code):
    if not isinstance(code, int):
        return ""
    names = {800: "পরিষ্কার আকাশ", 801: "হালকা মেঘ", 802: "আংশিক মেঘলা",
             803: "মেঘলা আকাশ", 804: "মেঘলা আকাশ"}
    if code in names:
        return names[code]
    groups = {2: "বজ্রসহ বৃষ্টি", 3: "গুঁড়ি গুঁড়ি বৃষ্টি", 5: "বৃষ্টি",
              6: "তুষারপাত", 7: "কুয়াশা / ধোঁয়াশা"}
    return groups.get(code // 100, "")


def shape_weather(data):
    """Pick the fields we show. Missing optional fields (e.g. no country over the sea,
    empty city name for open coordinates) no longer crash the request."""
    main = data.get("main") or {}
    wind = data.get("wind") or {}
    condition = (data.get("weather") or [{}])[0]
    icon = condition.get("icon", "")
    temp = main["temp"]  # KeyError here = unusable answer
    return {
        "city": (data.get("name") or "").strip(),
        "country": (data.get("sys") or {}).get("country", ""),
        "temperature": round(temp),
        "feels_like": round(main.get("feels_like", temp)),
        "humidity": main.get("humidity"),
        "wind_speed": wind.get("speed"),
        "description": condition.get("description", ""),
        "summary": condition_bn(condition.get("id")),
        "icon": icon if ICON_RE.match(icon) else "",
    }


def fetch_weather(params, cache_key):
    now = time.monotonic()
    with _cache_lock:
        cached = _cache.get(cache_key)
        if cached and cached[0] > now:
            return cached[1]

    if rate_limited("upstream", "all", UPSTREAM_PER_MINUTE, 60):
        raise WeatherError("সার্ভার এখন ব্যস্ত, এক মিনিট পরে আবার চেষ্টা করুন।", 429)
    try:
        reply = requests.get(
            OWM_URL, params={**params, "appid": API_KEY, "units": "metric"}, timeout=8
        )
    except requests.RequestException:
        raise WeatherError("আবহাওয়ার সার্ভারে পৌঁছানো যাচ্ছে না। একটু পরে আবার চেষ্টা করুন।", 502)

    if reply.status_code == 404:
        raise WeatherError("শহরটি খুঁজে পাওয়া যায়নি। নামের বানান ঠিক আছে কিনা দেখুন।", 404)
    if reply.status_code in (401, 403):
        app.logger.error("OpenWeatherMap rejected the API key (HTTP %s).", reply.status_code)
        raise WeatherError("আবহাওয়া সেবায় সাময়িক সমস্যা চলছে। পরে আবার চেষ্টা করুন।", 503)
    if reply.status_code == 429:
        raise WeatherError("সার্ভার এখন ব্যস্ত, এক মিনিট পরে আবার চেষ্টা করুন।", 429)
    if reply.status_code != 200:
        app.logger.error("OpenWeatherMap returned HTTP %s.", reply.status_code)
        raise WeatherError("আবহাওয়ার তথ্য আনা যায়নি। আবার চেষ্টা করুন।", 502)
    try:
        payload = shape_weather(reply.json())
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        raise WeatherError("আবহাওয়ার সার্ভার থেকে অপ্রত্যাশিত উত্তর এসেছে।", 502)

    with _cache_lock:
        if len(_cache) > 500:
            for key in [k for k, v in _cache.items() if v[0] <= now]:
                del _cache[key]
            if len(_cache) > 500:
                _cache.clear()
        _cache[cache_key] = (now + CACHE_TTL, payload)
    return payload


# --------------------------------------------------------------------------
# Public pages and API
# --------------------------------------------------------------------------
@app.get("/")
def home():
    # No database work here: crawlers and health checks no longer create fake visitors.
    return render_template("home.html", retention_days=RETENTION_DAYS)


@app.get("/api/weather")
def api_weather():
    """GET /api/weather?lat=..&lon=..   (visitor's location)
       GET /api/weather?city=..         (manual search)"""
    if not API_KEY_OK:
        return jsonify(ok=False, error="আবহাওয়া সেবা এখনো চালু করা হয়নি।"), 503
    if rate_limited("weather", client_ip(), 60, 60):
        return jsonify(ok=False, error="অনেক বেশি অনুরোধ হয়েছে। এক মিনিট পরে আবার চেষ্টা করুন।"), 429

    lat = parse_float(request.args.get("lat"), -90, 90)
    lon = parse_float(request.args.get("lon"), -180, 180)
    city = " ".join(request.args.get("city", "").split())

    if lat is not None and lon is not None:
        # ~1 km rounding: better cache hits and we pass on less precise data.
        params = {"lat": round(lat, 2), "lon": round(lon, 2)}
        key = ("geo", params["lat"], params["lon"])
    elif city:
        if len(city) > 80 or not city.isprintable():
            return jsonify(ok=False, error="শহরের নাম সঠিক নয়।"), 400
        params = {"q": city}
        key = ("city", city.casefold())
    else:
        return jsonify(ok=False, error="শহরের নাম লিখুন অথবা লোকেশন দিন।"), 400

    try:
        weather = fetch_weather(params, key)
    except WeatherError as error:
        return jsonify(ok=False, error=error.message), error.status
    return jsonify(ok=True, weather=weather)


@app.post("/api/location")
def api_location():
    if rate_limited("track", client_ip(), 600, 60):
        return jsonify(ok=False, error="Too many requests."), 429
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    latitude = parse_float(data.get("latitude"), -90, 90)
    longitude = parse_float(data.get("longitude"), -180, 180)
    if latitude is None or longitude is None:
        return jsonify(ok=False, error="Invalid location data."), 400
    accuracy = parse_float(data.get("accuracy"), 0, 1_000_000)

    visitor_id, is_new = visitor_from_request()
    record_visit(visitor_id, coords=(latitude, longitude, accuracy),
                 place=clean_place(data.get("place")))
    return with_visitor_cookie(jsonify(ok=True), visitor_id, is_new)


@app.post("/api/heartbeat")
def api_heartbeat():
    if rate_limited("track", client_ip(), 600, 60):
        return jsonify(ok=False, error="Too many requests."), 429
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    seconds = parse_float(data.get("active_seconds"), 0, 3600) or 0.0

    visitor_id, is_new = visitor_from_request()
    record_visit(visitor_id, claimed_seconds=seconds)
    return with_visitor_cookie(jsonify(ok=True), visitor_id, is_new)


# --------------------------------------------------------------------------
# Admin
# --------------------------------------------------------------------------
def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            if request.path.startswith("/admin/live"):
                return jsonify(ok=False, error="login"), 401
            return redirect(url_for("admin_login"))
        if request.method == "POST" and not same(
            request.form.get("csrf_token", ""), session.get("csrf", "")
        ):
            abort(400, "Invalid or missing CSRF token. Reload the page and try again.")
        return view(*args, **kwargs)

    return wrapped


@app.context_processor
def inject_csrf():
    def csrf_token():
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(16)
        return session["csrf"]

    return {"csrf_token": csrf_token}


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        ip = client_ip()
        if count_hits("login-ip", ip, 900) >= 5 or count_hits("login-all", "all", 900) >= 30:
            flash("অনেকবার ভুল চেষ্টা হয়েছে। ১৫ মিনিট পরে আবার চেষ্টা করুন।")
            return render_template("admin_login.html"), 429
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        valid = ADMIN_ENABLED & same(username, ADMIN_USERNAME) & same(password, ADMIN_PASSWORD)
        if valid:
            session.clear()
            session.permanent = True
            session["admin_logged_in"] = True
            session["csrf"] = secrets.token_hex(16)
            return redirect(url_for("admin_dashboard"))
        add_hit("login-ip", ip)
        add_hit("login-all", "all")
        flash("ইউজারনেম বা পাসওয়ার্ড ভুল।" if ADMIN_ENABLED
              else "অ্যাডমিন লগইন বন্ধ আছে — .env ফাইলে ADMIN_PASSWORD দিন।")
    return render_template("admin_login.html")


@app.post("/admin/logout")
@admin_required
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


def dashboard_data():
    db = get_db()
    now = utcnow()
    online_cutoff = iso(now - timedelta(seconds=ONLINE_SECONDS))
    totals = db.execute(
        """SELECT COUNT(*) AS total,
                  COALESCE(SUM(CASE WHEN last_latitude IS NOT NULL THEN 1 END), 0) AS located,
                  COALESCE(SUM(CASE WHEN last_seen >= ? THEN 1 END), 0) AS online,
                  COALESCE(SUM(location_updates), 0) AS updates,
                  COALESCE(SUM(total_active_seconds), 0) AS active
           FROM visitors""",
        (online_cutoff,),
    ).fetchone()
    rows = db.execute("SELECT * FROM visitors ORDER BY last_seen DESC LIMIT 500").fetchall()
    stats = {
        "online": str(totals["online"]),
        "total": str(totals["total"]),
        "located": str(totals["located"]),
        "updates": str(totals["updates"]),
        "active": fmt_duration(totals["active"]),
    }
    return stats, [present(row, now) for row in rows]


def present(row, now):
    last_seen = parse_iso(row["last_seen"])
    age = (now - last_seen).total_seconds() if last_seen else None
    located_at = parse_iso(row["location_updated_at"])
    located_age = (now - located_at).total_seconds() if located_at else None
    lat, lon, acc = row["last_latitude"], row["last_longitude"], row["last_accuracy"]
    has_location = lat is not None and lon is not None
    return {
        "id": row["id"],
        "short_id": row["visitor_id"][:8],
        "online": age is not None and age <= ONLINE_SECONDS,
        "first_seen": fmt_local(row["first_seen"]),
        "last_seen": fmt_local(row["last_seen"]),
        "ago": fmt_ago(age),
        "place": row["place_name"] or "",
        "has_location": has_location,
        "coords": f"{lat:.5f}, {lon:.5f}" if has_location else "",
        "map_url": f"https://www.google.com/maps?q={lat:.6f},{lon:.6f}" if has_location else "",
        "accuracy": f"±{acc:.0f} m" if acc is not None else "",
        "location_ago": fmt_ago(located_age) if located_age is not None else "",
        "active": fmt_duration(row["total_active_seconds"]),
        "updates": row["location_updates"],
    }


@app.get("/admin")
@admin_required
def admin_dashboard():
    stats, visitors = dashboard_data()
    return render_template("admin.html", stats=stats, visitors=visitors)


@app.get("/admin/live")
@admin_required
def admin_live():
    stats, visitors = dashboard_data()
    return jsonify(ok=True, stats=stats, rows=render_template("_rows.html", visitors=visitors))


@app.post("/admin/delete/<int:visitor_db_id>")
@admin_required
def delete_visitor(visitor_db_id):
    db = get_db()
    db.execute("DELETE FROM visitors WHERE id = ?", (visitor_db_id,))
    db.commit()
    flash("ভিজিটরের রেকর্ড মুছে ফেলা হয়েছে।")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/delete-all")
@admin_required
def delete_all_visitors():
    db = get_db()
    db.execute("DELETE FROM visitors")
    db.commit()
    flash("সব ভিজিটর রেকর্ড মুছে ফেলা হয়েছে।")
    return redirect(url_for("admin_dashboard"))


# --------------------------------------------------------------------------
# Headers and errors
# --------------------------------------------------------------------------
@app.after_request
def add_security_headers(response):
    response.headers.setdefault("Content-Security-Policy", CSP)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("Permissions-Policy", "geolocation=(self)")
    if request.path.startswith(("/admin", "/api")):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


@app.errorhandler(HTTPException)
def http_error(error):
    if request.path.startswith("/api/"):
        return jsonify(ok=False, error=error.description), error.code
    return error


@app.errorhandler(sqlite3.Error)
def database_error(error):
    app.logger.exception("Database error: %s", error)
    if request.path.startswith("/api/"):
        return jsonify(ok=False, error="সার্ভার এখন ব্যস্ত, একটু পরে আবার চেষ্টা করুন।"), 503
    return InternalServerError()


init_db()

if __name__ == "__main__":
    # Local use only. On PythonAnywhere the WSGI file imports `app`; never run this there.
    app.run(host="127.0.0.1", port=env_int("PORT", 5000), debug=DEBUG)
