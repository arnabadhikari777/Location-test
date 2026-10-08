<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0d05a4,50:9ec533,100:0d05a4&height=200&section=header&text=My%20Weather%20App&fontSize=56&fontColor=ffffff&animation=fadeIn&fontAlignY=40&desc=Current%20weather%20for%20any%20city%20%E2%80%94%20Flask%20%C2%B7%20OpenWeatherMap&descAlignY=58&descSize=18" width="100%" alt="My Weather App banner"/>

[![Typing SVG](https://readme-typing-svg.demolab.com/?font=Fira+Code&weight=600&size=20&duration=2800&pause=900&color=9EC533&center=true&vCenter=true&multiline=true&repeat=true&width=700&height=80&lines=Search+any+city+%E2%86%92+live+temperature;Humidity+%26+wind+speed+in+one+card;Clean+mobile-first+UI+%C2%B7+OpenWeatherMap)](https://git.io/typing-svg)

<p>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Flask-3.1-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask"/>
  <img src="https://img.shields.io/badge/OpenWeatherMap-API-EB6E4B?style=for-the-badge&logo=openweathermap&logoColor=white" alt="OpenWeatherMap"/>
  <img src="https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white" alt="HTML5"/>
  <img src="https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white" alt="CSS3"/>
  <img src="https://img.shields.io/badge/JavaScript-ES6-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black" alt="JavaScript"/>
</p>

<p>
  <a href="https://my-weather-app-ikey.onrender.com">
    <img src="https://img.shields.io/badge/Live_Demo-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white" alt="Live Demo"/>
  </a>
</p>

</div>

---

## 📖 Overview

**My Weather App** shows the **current weather for your own location** the moment you open it: the browser asks for location permission and the weather appears automatically. Prefer another place? Type a city name and search — no reload needed.

The site owner also gets a password-protected **admin panel** (`/admin`) listing every visitor with their live location, online status and time spent on the site.

---

## ✨ Features

- 📍 **Automatic weather** from the browser location (coordinates go to OpenWeatherMap, which returns the area name)
- 🔍 **City search** without a page reload
- 🌡️ Temperature, feels-like, humidity, wind speed and the official icon
- 🛡️ **Admin panel** — online status, map link per visitor, auto-refresh every 10 s, delete records
- 🔐 Secrets only in `.env`; CSRF protection, login rate-limit, strict security headers
- 🧹 Visitor data is deleted automatically after 30 days of inactivity (configurable)

---

## 📁 Project Structure

```
My-weather-app/
├── weather.py              # Flask app, weather API, tracking API, admin
├── requirements.txt
├── .env.example            # copy to .env and fill in
├── templates/
│   ├── home.html           # public page
│   ├── admin.html / _rows.html / admin_login.html
└── static/
    ├── style.css, script.js          # public page
    └── admin.css, admin.js           # admin panel
```

---

## 🚀 Run locally

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # fill in the values; add FLASK_DEBUG=1 for local use
python weather.py
```

Open **http://127.0.0.1:5000**. Location needs HTTPS or `localhost`.

---

## 🌐 How it works

1. On load the page asks the browser for the location.
2. Allowed → `GET /api/weather?lat=..&lon=..` → OpenWeatherMap → the card fills in automatically.
3. Denied or unavailable → a message explains why, and the city search still works (`GET /api/weather?city=..`).
4. With permission, the location is reported to `/api/location` (throttled: only after real movement) and visible time is counted via `/api/heartbeat`.
5. Weather answers are cached for 10 minutes and OpenWeatherMap calls are capped, so nobody can burn the API quota.

---

## 📦 Deployment

PythonAnywhere: see [PYTHONANYWHERE_SETUP.md](PYTHONANYWHERE_SETUP.md).
Any other host: `gunicorn weather:app` with the same environment variables.

---


## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

<div align="center">

Made with ☀️ by [Arnab Adhikari](https://github.com/arnabadhikari777)

Weather data provided by [OpenWeatherMap](https://openweathermap.org/)

</div>
