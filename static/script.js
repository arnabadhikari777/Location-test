const cityInput = document.getElementById("city-input");

if (cityInput) {
    cityInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
            event.preventDefault();
            cityInput.form.requestSubmit();
        }
    });
}

// Location tracking starts automatically after the browser asks for permission.
(function startLocationTracking() {
    if (!navigator.geolocation) {
        console.warn("Geolocation is not supported by this browser.");
        return;
    }

    function sendLocation(position) {
        fetch("/api/location", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            body: JSON.stringify({
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
                accuracy: position.coords.accuracy
            })
        }).catch(() => {});
    }

    function locationError(error) {
        console.warn("Location permission/error:", error.message);
    }

    navigator.geolocation.watchPosition(sendLocation, locationError, {
        enableHighAccuracy: true,
        maximumAge: 10000,
        timeout: 15000
    });
})();

// Record active usage time in short heartbeats.
(function startUsageTracking() {
    let lastBeat = Date.now();

    function sendHeartbeat() {
        const now = Date.now();
        const seconds = Math.max(0, Math.min((now - lastBeat) / 1000, 60));
        lastBeat = now;

        fetch("/api/heartbeat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            keepalive: true,
            body: JSON.stringify({ active_seconds: seconds })
        }).catch(() => {});
    }

    setInterval(sendHeartbeat, 15000);
    window.addEventListener("pagehide", sendHeartbeat);
})();
