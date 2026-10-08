# PythonAnywhere setup

## Environment variables
Set these in your PythonAnywhere environment (or otherwise securely load them):
- OPENWEATHER_API_KEY
- FLASK_SECRET_KEY
- ADMIN_USERNAME
- ADMIN_PASSWORD
- DATABASE_PATH (optional; recommended as an absolute path to weather.db)

## WSGI
Point the PythonAnywhere WSGI file to this project and import:

from weather import app as application

Do not run `app.run()` for the hosted site.

## Database
The app creates `weather.db` automatically on first import/run. On PythonAnywhere, use an absolute DATABASE_PATH so the database stays in your persistent home directory.

## Admin
Open `/admin` and sign in using ADMIN_USERNAME and ADMIN_PASSWORD.

## Location
The browser requests location permission automatically. If allowed, `watchPosition()` sends latitude, longitude and accuracy to `/api/location` whenever the browser reports a new position.

## Important
Geolocation requires a secure context (HTTPS). PythonAnywhere's HTTPS site supports this.
