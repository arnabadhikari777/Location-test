# PythonAnywhere Setup

## 1. Upload the files
Replace all project files in the project folder (for example `/home/YOURNAME/My-weather-app/`) with the new files.
Do not delete your existing `.env` or `weather.db` — the new code can continue using the old database.

## 2. Install packages
In the Bash console (with your virtual environment active):

    pip install -r requirements.txt

## 3. `.env` file (inside the project folder)
Copy `.env.example` to `.env` and update all values:

- `OPENWEATHER_API_KEY` — your OpenWeatherMap API key
- `FLASK_SECRET_KEY` — a long random value. Generate it with: `python -c "import secrets; print(secrets.token_hex(32))"`
- `ADMIN_USERNAME`, `ADMIN_PASSWORD` — a strong password with at least 10 characters
- (optional) `DATABASE_PATH`, `VISITOR_RETENTION_DAYS`, `DISPLAY_TIMEZONE`

> PythonAnywhere does not provide a separate "Environment variables" box for web apps — use the `.env` file instead.
> The app reads `.env` from the project folder, so it does not matter which directory you start it from.
> If `FLASK_SECRET_KEY` is missing or still contains a placeholder, the app intentionally refuses to start (the reason will appear in the Error log).

## 4. WSGI file
In the Web tab, set the WSGI configuration file to:

    import sys
    path = "/home/YOURNAME/My-weather-app"
    if path not in sys.path:
        sys.path.insert(0, path)

    from weather import app as application

Do not run `app.run()` on a live site.

## 5. HTTPS
Enable **Force HTTPS** in the Web tab. Browser geolocation works only over HTTPS, and the admin cookie also runs in secure mode.

## 6. Reload
Click the green **Reload** button in the Web tab.

## Usage
- Site: `https://YOURNAME.pythonanywhere.com/`
- Admin: `/admin` (login at `/admin/login`) — the panel auto-refreshes every 10 seconds.
- After 5 failed password attempts, login is blocked for 15 minutes.
- If anything is wrong, check the **Error log** in the Web tab.
