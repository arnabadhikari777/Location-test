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

**My Weather App** is a simple, clean Flask web app that shows the **current weather** for any city you search.

Type a city name → hit Search → get temperature (°C), weather description, humidity, wind speed, and the official OpenWeatherMap icon — all in a modern glass-style card with a gradient background.

> Built for learning: Flask routing, form handling, environment variables, external API calls, and a responsive frontend.

**Live demo:** [my-weather-app-ikey.onrender.com](https://my-weather-app-ikey.onrender.com)

---

## ✨ Features

- 🔍 **City search** — enter any city name and get live weather
- 🌡️ **Temperature** in Celsius (rounded)
- 📝 **Weather description** + official OpenWeatherMap icon
- 💧 **Humidity** percentage
- 💨 **Wind speed** in m/s
- ⚠️ Clear error messages (empty input, city not found, invalid API key, network issues)
- 📱 **Mobile-first** responsive UI
- 🔐 API key kept in `.env` (never committed)

---

## 🛠️ Tech Stack

| Layer        | Technology                          |
|--------------|-------------------------------------|
| Backend      | Python, Flask 3.1                   |
| API          | OpenWeatherMap Current Weather API  |
| Config       | python-dotenv                       |
| Frontend     | HTML5, CSS3, Vanilla JS             |
| Deployment   | Render (gunicorn)                   |

---

## 📁 Project Structure

```
My-weather-app/
├── weather.py          # Flask app + OpenWeatherMap logic
├── requirements.txt    # Python dependencies
├── .gitignore          # Ignores .venv and .env
├── templates/
│   └── home.html       # Main page template
└── static/
    ├── style.css       # Gradient + glass card UI
    └── script.js       # Enter-key form submit helper
```

---

## 🚀 Getting Started

### Prerequisites

- Python **3.10+**
- A free [OpenWeatherMap](https://openweathermap.org/api) API key

### 1 · Clone the repository

```bash
git clone https://github.com/arnabadhikari777/My-weather-app.git
cd My-weather-app
```

### 2 · Create virtual environment & install dependencies

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3 · Set your API key

Create a `.env` file in the project root:

```env
OPENWEATHER_API_KEY=your_api_key_here
```

> Get a free key from [OpenWeatherMap](https://home.openweathermap.org/api_keys).  
> The file is already listed in `.gitignore` so it will not be pushed.

### 4 · Run the app

```bash
python weather.py
```

Open **http://127.0.0.1:5000** in your browser.

---

## 🌐 How it works

1. User submits a city name via the form (POST).
2. Flask reads `OPENWEATHER_API_KEY` from the environment.
3. A request is sent to:
   ```
   https://api.openweathermap.org/data/2.5/weather?q={city}&appid={key}&units=metric
   ```
4. On success, temperature, description, humidity, wind speed and icon are extracted and passed to the template.
5. On failure, a friendly error message is shown (404 city, 401 key, network, etc.).

---

## 📦 Deployment (Render)

The project is already configured for Render:

- `requirements.txt` includes `gunicorn`
- Set environment variable `OPENWEATHER_API_KEY` in the Render dashboard
- Start command example:
  ```bash
  gunicorn weather:app
  ```

Live instance: [https://my-weather-app-ikey.onrender.com](https://my-weather-app-ikey.onrender.com)

---

## 🗺️ Roadmap

- [ ] 5-day forecast
- [ ] Geolocation (auto-detect city)
- [ ] Dark / light theme toggle
- [ ] Search history (localStorage)

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

<div align="center">

Made with ☀️ by [Arnab Adhikari](https://github.com/arnabadhikari777)

Weather data provided by [OpenWeatherMap](https://openweathermap.org/)

</div>
