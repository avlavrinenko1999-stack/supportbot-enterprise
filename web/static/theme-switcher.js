(function () {
  "use strict";
  var STORAGE_KEY = "supportbot-theme-mode";
  var root = document.documentElement;
  var timer = 0;

  function automaticTheme() {
    var hour = new Date().getHours();
    return hour >= 7 && hour < 20 ? "day" : "night";
  }

  function storedMode() {
    try {
      var value = window.localStorage.getItem(STORAGE_KEY);
      if (value === "day" || value === "night" || value === "auto") return value;
    } catch (ignore) {}
    return "auto";
  }

  function apply(mode, save) {
    var theme = mode === "auto" ? automaticTheme() : mode;
    root.setAttribute("data-theme-mode", mode);
    root.setAttribute("data-theme", theme);
    var themeMeta = document.querySelector('meta[name="theme-color"]');
    if (themeMeta) themeMeta.setAttribute("content", theme === "day" ? "#f3efe6" : "#090b0e");
    if (save) {
      try { window.localStorage.setItem(STORAGE_KEY, mode); } catch (ignore) {}
    }
    var buttons = document.querySelectorAll(".theme-switch-button");
    for (var index = 0; index < buttons.length; index += 1) {
      var active = buttons[index].getAttribute("data-theme-choice") === mode;
      buttons[index].className = "theme-switch-button" + (active ? " is-active" : "");
      buttons[index].setAttribute("aria-pressed", active ? "true" : "false");
    }
    var event;
    try {
      event = new CustomEvent("supportbot-theme-change", { detail: { theme: theme, mode: mode } });
    } catch (ignoreEvent) {
      event = document.createEvent("CustomEvent");
      event.initCustomEvent("supportbot-theme-change", false, false, { theme: theme, mode: mode });
    }
    window.dispatchEvent(event);
  }

  function refreshAutomatic() {
    if (root.getAttribute("data-theme-mode") === "auto") apply("auto", false);
  }

  function initialize() {
    var buttons = document.querySelectorAll(".theme-switch-button");
    for (var index = 0; index < buttons.length; index += 1) {
      buttons[index].onclick = function () {
        apply(this.getAttribute("data-theme-choice"), true);
      };
    }
    apply(storedMode(), false);
    window.clearInterval(timer);
    timer = window.setInterval(refreshAutomatic, 60000);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize, false);
  else initialize();
}());
