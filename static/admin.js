(() => {
  "use strict";

  // Confirm dialogs (inline onsubmit handlers are blocked by the page's CSP).
  document.addEventListener("submit", (event) => {
    const message = event.target.dataset && event.target.dataset.confirm;
    if (message && !window.confirm(message)) event.preventDefault();
  });

  const rows = document.getElementById("rows");
  const stamp = document.getElementById("updated-at");
  if (!rows) return;

  async function refresh() {
    if (document.hidden) return;
    try {
      const res = await fetch("/admin/live", {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      });
      if (res.status === 401) { window.location.href = "/admin/login"; return; }
      if (!res.ok) return;
      const data = await res.json();
      rows.innerHTML = data.rows; // our own server-rendered markup; Jinja already escaped every value
      Object.keys(data.stats).forEach((key) => {
        const node = document.querySelector('[data-stat="' + key + '"]');
        if (node) node.textContent = data.stats[key];
      });
      if (stamp) stamp.textContent = new Date().toLocaleTimeString();
    } catch (_) { /* network blip: try again next tick */ }
  }

  setInterval(refresh, 10000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
})();
