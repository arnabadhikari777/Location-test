/* Weather page
   - asks for the browser location on load and shows that area's weather automatically
   - manual city search (no page reload)
   - with the visitor's permission: reports location to the admin panel (throttled)
     and counts time spent while the tab is visible */
(() => {
  "use strict";

  const REFRESH_MS = 10 * 60 * 1000; // refresh the shown weather every 10 minutes
  const HEARTBEAT_MS = 15 * 1000;    // "still here" ping while the tab is visible
  const MIN_SEND_MS = 15 * 1000;     // never report location more often than this...
  const MIN_MOVE_M = 50;             // ...and only after moving at least this far

  const $ = (id) => document.getElementById(id);
  const el = {
    card: $("weather-card"), label: $("source-label"), place: $("place"),
    desc: $("weather-description"), icon: $("weather-icon"), temp: $("temperature"),
    feels: $("feels-like"), humidity: $("humidity"), wind: $("wind"), status: $("status"),
    form: $("search-form"), input: $("city-input"), button: $("search-button"),
    locate: $("locate-button"),
  };

  let current = null;   // what is on screen: {type:"coords",lat,lon} | {type:"city",city}
  let requestId = 0;    // only the newest request may update the screen
  let controller = null;
  let lastPlace = "";
  let lastSent = { t: 0, lat: null, lon: null };
  let tracking = false;
  let visibleSince = document.hidden ? null : Date.now();

  function setStatus(text, kind) {
    el.status.textContent = text;
    el.status.className = "status-message" + (kind ? " " + kind : "");
  }

  async function api(path, options) {
    let res;
    try {
      res = await fetch(path, Object.assign({ credentials: "same-origin" }, options));
    } catch (err) {
      if (err && err.name === "AbortError") throw err;
      throw new Error("Check your internet connection and try again.");
    }
    let body = null;
    try { body = await res.json(); } catch (_) { /* not JSON */ }
    if (!res.ok || !body || body.ok === false) {
      throw new Error((body && body.error) || "Something went wrong. Please try again.");
    }
    return body;
  }

  // ---------- weather ----------
  function render(w, target) {
    const place = [w.city, w.country].filter(Boolean).join(", ");
    // The label sent to the admin panel must describe where the visitor IS,
    // not a city they merely searched for.
    if (target.type === "coords") lastPlace = place;
    el.place.textContent = place || "Your area";
    el.desc.textContent = w.summary || w.description || "";
    el.desc.title = w.description || "";
    el.temp.textContent = String(w.temperature);
    el.feels.textContent = w.feels_like != null ? "Feels like " + w.feels_like + "°C" : "";
    el.humidity.textContent = w.humidity != null ? w.humidity + "%" : "--";
    el.wind.textContent = w.wind_speed != null ? w.wind_speed + " m/s" : "--";
    el.label.textContent = target.type === "coords"
      ? "📍 Weather for your location" : "🔎 Weather for the searched city";
    if (w.icon) {
      const img = document.createElement("img");
      img.src = "https://openweathermap.org/img/wn/" + w.icon + "@2x.png";
      img.alt = w.description || "";
      el.icon.replaceChildren(img);
    } else {
      el.icon.textContent = "🌤️";
    }
    el.locate.hidden = target.type === "coords";
    const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    setStatus("Last updated: " + time);
  }

  async function loadWeather(target, opts) {
    const silent = !!(opts && opts.silent);
    const id = ++requestId;
    if (controller) controller.abort();
    controller = new AbortController();
    if (!silent) {
      el.card.classList.add("is-loading");
      el.button.disabled = true;
      setStatus("Loading weather information…");
    }
    const query = target.type === "coords"
      ? new URLSearchParams({ lat: target.lat.toFixed(3), lon: target.lon.toFixed(3) })
      : new URLSearchParams({ city: target.city });
    try {
      const body = await api("/api/weather?" + query, { signal: controller.signal });
      if (id !== requestId) return false;
      current = target;
      render(body.weather, target);
      return true;
    } catch (err) {
      if ((err && err.name === "AbortError") || id !== requestId) return false;
      if (!silent) setStatus(err.message, "error"); // keep the old data on screen
      return false;
    } finally {
      if (id === requestId) {
        el.card.classList.remove("is-loading");
        el.button.disabled = false;
      }
    }
  }

  // ---------- location ----------
  function getPosition() {
    return new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy: false, // weather doesn't need GPS precision (saves battery)
        timeout: 15000,
        maximumAge: 5 * 60 * 1000,
      });
    });
  }

  function showGeoError(err) {
    el.locate.hidden = false;
    const code = err && err.code;
    if (code === 1) {
      setStatus("Location permission was denied. Enable location in the browser site settings or search by city.", "error");
    } else if (code === 3) {
      setStatus("Location detection is taking too long. Please try again or search by city.", "error");
    } else {
      setStatus("Your location could not be determined. Please search by city instead.", "error");
    }
  }

  function distanceM(lat1, lon1, lat2, lon2) { // haversine
    const rad = Math.PI / 180;
    const dLat = (lat2 - lat1) * rad;
    const dLon = (lon2 - lon1) * rad;
    const a = Math.sin(dLat / 2) ** 2 +
      Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLon / 2) ** 2;
    return 2 * 6371000 * Math.asin(Math.min(1, Math.sqrt(a)));
  }

  function reportLocation(pos) {
    const c = pos.coords;
    lastSent = { t: Date.now(), lat: c.latitude, lon: c.longitude };
    fetch("/api/location", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        latitude: c.latitude, longitude: c.longitude, accuracy: c.accuracy, place: lastPlace,
      }),
    }).catch(() => {});
  }

  function onWatch(pos) {
    if (document.hidden) return; // no reporting from background tabs
    const c = pos.coords;
    const moved = lastSent.lat === null
      ? Infinity : distanceM(lastSent.lat, lastSent.lon, c.latitude, c.longitude);
    // GPS/network jitter is not movement: require more than the reported accuracy.
    if (moved >= Math.max(MIN_MOVE_M, c.accuracy || 0) && Date.now() - lastSent.t >= MIN_SEND_MS) {
      reportLocation(pos);
    }
  }

  function startTracking() {
    if (tracking) return;
    tracking = true;
    navigator.geolocation.watchPosition(onWatch, () => {}, {
      enableHighAccuracy: false, maximumAge: 30000, timeout: 60000,
    });
  }

  async function useMyLocation(force) {
    if (!("geolocation" in navigator)) {
      setStatus("Geolocation is not supported in this browser. Please search by city instead.", "error");
      return;
    }
    el.locate.disabled = true;
    setStatus("Getting location… if the browser asks for permission, click ‘Allow’.");
    let pos;
    try {
      pos = await getPosition();
    } catch (err) {
      el.locate.disabled = false;
      if (force || !current) showGeoError(err); else el.locate.hidden = false;
      return;
    }
    el.locate.disabled = false;
    // If the visitor already searched a city while the permission prompt was open, keep it.
    if (force || !current) {
      await loadWeather({ type: "coords", lat: pos.coords.latitude, lon: pos.coords.longitude });
    }
    reportLocation(pos);
    startTracking();
  }

  // ---------- time on site (only while the tab is visible) ----------
  function sendBeat() {
    if (visibleSince === null) return;
    const now = Date.now();
    const seconds = Math.min((now - visibleSince) / 1000, 60);
    visibleSince = document.hidden ? null : now;
    fetch("/api/heartbeat", {
      method: "POST",
      credentials: "same-origin",
      keepalive: true,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ active_seconds: seconds }),
    }).catch(() => {});
  }

  // ---------- wiring ----------
  el.form.addEventListener("submit", (event) => {
    event.preventDefault();
    const city = el.input.value.trim().replace(/\s+/g, " ");
    if (!city) {
      setStatus("Please enter a city name.", "error");
      el.input.focus();
      return;
    }
    loadWeather({ type: "city", city: city });
  });

  el.locate.addEventListener("click", () => useMyLocation(true));

  setInterval(() => {
    if (document.hidden || !current) return;
    const target = current.type === "coords" && lastSent.lat !== null
      ? { type: "coords", lat: lastSent.lat, lon: lastSent.lon } : current;
    loadWeather(target, { silent: true });
  }, REFRESH_MS);

  setInterval(() => { if (!document.hidden) sendBeat(); }, HEARTBEAT_MS);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) sendBeat(); else visibleSince = Date.now();
  });
  window.addEventListener("pagehide", sendBeat);

  async function init() {
    sendBeat(); // registers the visit right away (0 seconds)
    if (!("geolocation" in navigator)) {
      useMyLocation(false);
      return;
    }
    try {
      if (navigator.permissions && navigator.permissions.query) {
        const perm = await navigator.permissions.query({ name: "geolocation" });
        // If the visitor allows location later (browser settings), start automatically.
        perm.onchange = () => { if (perm.state === "granted" && !tracking) useMyLocation(false); };
        if (perm.state === "denied") {
          showGeoError({ code: 1 });
          return;
        }
      }
    } catch (_) { /* Permissions API unsupported: just ask */ }
    useMyLocation(false);
  }

  init();
})();
