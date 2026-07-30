(function () {
  "use strict";

  var lastInput = Date.now();
  var sending = false;
  var activityEvents = ["pointerdown", "pointermove", "keydown", "wheel", "touchstart"];

  function markActive() { lastInput = Date.now(); }
  activityEvents.forEach(function (name) {
    window.addEventListener(name, markActive, { passive: true });
  });

  function updatePresence(data) {
    Object.keys(data || {}).forEach(function (id) {
      var value = data[id];
      document.querySelectorAll('[data-presence-account="' + id + '"]').forEach(function (root) {
        var label = root.querySelector("[data-presence-label]");
        var login = root.querySelector("[data-presence-login]");
        var workday = root.querySelector("[data-presence-workday]");
        var source = root.querySelector("[data-presence-source]");
        if (label) {
          label.textContent = value.label;
          label.classList.remove("presence-working", "presence-idle", "presence-away", "presence-disabled");
          label.classList.add("presence-" + value.code);
        }
        if (login) login.textContent = value.login;
        if (workday) workday.textContent = value.workday_start;
        if (source) source.textContent = value.source === "agent" ? "Агент рабочего ПК" : value.source === "browser" ? "Браузер" : value.source === "manual" ? "Указано сотрудником" : "Сбор отключён";
      });
    });
  }

  function refreshVisibleStatuses() {
    var ids = Array.from(document.querySelectorAll("[data-presence-account]"))
      .map(function (node) { return node.getAttribute("data-presence-account"); })
      .filter(Boolean);
    if (!ids.length) return Promise.resolve();
    return fetch("/api/presence/statuses?ids=" + encodeURIComponent(Array.from(new Set(ids)).join(",")), {
      credentials: "same-origin", cache: "no-store"
    }).then(function (response) { return response.ok ? response.json() : {}; }).then(updatePresence);
  }

  function heartbeat() {
    if (sending) return;
    sending = true;
    var active = !document.hidden && Date.now() - lastInput < 90000;
    fetch("/api/presence/heartbeat", {
      method: "POST", credentials: "same-origin", cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ active: active })
    }).then(refreshVisibleStatuses).catch(function () {}).finally(function () { sending = false; });
  }

  document.addEventListener("visibilitychange", heartbeat);
  heartbeat();
  window.setInterval(heartbeat, 20000);
}());
