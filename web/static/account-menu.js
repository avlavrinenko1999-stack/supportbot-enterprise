(function () {
  "use strict";
  var menu = document.querySelector(".account-menu");
  if (!menu) return;
  var trigger = menu.querySelector(".account-menu-trigger");
  var panel = menu.querySelector(".account-menu-panel");
  var mainScreen = menu.querySelector(".account-menu-main");
  var workScreen = menu.querySelector(".account-work-screen");
  var absenceReasons = menu.querySelector(".account-absence-reasons");
  var officialStatuses = menu.querySelector(".account-official-statuses");

  function showWorkScreen(show) {
    if (!mainScreen || !workScreen) return;
    mainScreen.hidden = show;
    workScreen.hidden = !show;
    if (absenceReasons) absenceReasons.hidden = true;
    if (officialStatuses) officialStatuses.hidden = true;
  }

  function setOpen(open) {
    trigger.setAttribute("aria-expanded", open ? "true" : "false");
    panel.hidden = !open;
    menu.classList.toggle("is-open", open);
    if (!open) showWorkScreen(false);
  }

  trigger.onclick = function () {
    setOpen(trigger.getAttribute("aria-expanded") !== "true");
  };
  document.addEventListener("click", function (event) {
    if (!menu.contains(event.target)) setOpen(false);
  });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      setOpen(false);
      trigger.focus();
    }
  });
  var openWorkStates = menu.querySelector("[data-open-work-states]");
  var closeWorkStates = menu.querySelector("[data-close-work-states]");
  var openAbsenceReasons = menu.querySelector("[data-open-absence-reasons]");
  var closeAbsenceReasons = menu.querySelector("[data-close-absence-reasons]");
  var openOfficialStatuses = menu.querySelector("[data-open-official-statuses]");
  var closeOfficialStatuses = menu.querySelector("[data-close-official-statuses]");
  if (openWorkStates) openWorkStates.onclick = function () { showWorkScreen(true); };
  if (closeWorkStates) closeWorkStates.onclick = function () { showWorkScreen(false); };
  if (openAbsenceReasons) openAbsenceReasons.onclick = function () {
    absenceReasons.hidden = false;
    menu.querySelectorAll(".account-work-screen > .account-work-action").forEach(function (node) { node.hidden = true; });
  };
  if (closeAbsenceReasons) closeAbsenceReasons.onclick = function () {
    absenceReasons.hidden = true;
    menu.querySelectorAll(".account-work-screen > .account-work-action").forEach(function (node) { node.hidden = false; });
    if (openAbsenceReasons && openAbsenceReasons.dataset.available !== "true") openAbsenceReasons.hidden = true;
  };
  if (openOfficialStatuses) openOfficialStatuses.onclick = function () {
    officialStatuses.hidden = false;
    menu.querySelectorAll(".account-work-screen > .account-work-action").forEach(function (node) { node.hidden = true; });
  };
  if (closeOfficialStatuses) closeOfficialStatuses.onclick = function () {
    officialStatuses.hidden = true;
    menu.querySelectorAll(".account-work-screen > .account-work-action").forEach(function (node) { node.hidden = false; });
    if (openAbsenceReasons && openAbsenceReasons.dataset.available !== "true") openAbsenceReasons.hidden = true;
  };

  function personalStatusLabel(data) { return data.state === "working" ? "Работаю" : data.label; }

  function renderWorkSnapshot(data) {
    menu.querySelectorAll(".account-work-current").forEach(function (node) { node.textContent = data.label; });
    var triggerStatus = menu.querySelector("[data-account-current-status]");
    if (triggerStatus) triggerStatus.textContent = personalStatusLabel(data);
    var workingButton = menu.querySelector('[data-work-state="working"]');
    var officialState = ["vacation", "sick_leave", "business_trip", "day_off"].indexOf(data.state) !== -1;
    if (workingButton) workingButton.textContent = (data.state === "not_started" || data.state === "finished") ? "Начать рабочий день" : "Вернуться к работе";
    if (workingButton) workingButton.hidden = data.state === "working" || officialState;
    if (openAbsenceReasons) { openAbsenceReasons.hidden = data.state !== "working"; openAbsenceReasons.dataset.available = data.state === "working" ? "true" : "false"; }
    var reminder = document.querySelector(".work-state-reminder");
    if (!data.reminder) { if (reminder) reminder.remove(); return; }
    if (!reminder) { reminder = document.createElement("div"); reminder.className = "work-state-reminder glass"; document.body.appendChild(reminder); }
    reminder.textContent = data.reminder;
  }
  function refreshWorkState() {
    fetch("/api/work-state/current", { credentials: "same-origin", cache: "no-store" })
      .then(function (response) { return response.ok ? response.json() : Promise.reject(); })
      .then(renderWorkSnapshot).catch(function () {});
  }

  function requestWorkState(button, state, reason, extra) {
    button.disabled = true;
    var payload = { state: state, reason: reason || "" };
    Object.keys(extra || {}).forEach(function (key) { payload[key] = extra[key]; });
    return fetch("/api/work-state", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-Requested-With": "SupportBot" },
      body: JSON.stringify(payload)
    }).then(function (response) { return response.json().then(function (data) { return { ok: response.ok, data: data }; }); })
      .then(function (result) {
        if (!result.ok) throw new Error(result.data.error || "Не удалось изменить статус");
        menu.querySelectorAll(".account-work-current").forEach(function (current) { current.textContent = result.data.label; });
        setOpen(false);
        refreshWorkState();
      }).catch(function (error) { window.alert(error.message); })
      .finally(function () { button.disabled = false; });
  }

  function requestOtherReason(button) {
    var overlay = document.createElement("div");
    overlay.className = "work-reason-overlay";
    overlay.innerHTML = '<form class="work-reason-dialog glass"><h2>Прочая причина</h2><p>Опишите причину отсутствия на рабочем месте.</p><textarea maxlength="500" required autofocus placeholder="Например: визит к врачу"></textarea><div class="work-reason-actions"><button type="button" class="button secondary-link" data-reason-cancel>Отмена</button><button type="submit" class="button">Подтверждаю</button></div></form>';
    document.body.appendChild(overlay);
    var form = overlay.querySelector("form");
    var textarea = overlay.querySelector("textarea");
    function close() { overlay.remove(); }
    overlay.querySelector("[data-reason-cancel]").onclick = close;
    overlay.addEventListener("click", function (event) { if (event.target === overlay) close(); });
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var reason = textarea.value.trim();
      if (!reason) { textarea.setCustomValidity("Укажите причину отсутствия."); textarea.reportValidity(); return; }
      close();
      requestWorkState(button, "other", reason, {});
    });
    window.setTimeout(function () { textarea.focus(); }, 0);
  }

  function requestOfficialPeriod(button, state) {
    var overlay = document.createElement("div");
    overlay.className = "work-reason-overlay";
    var current = new Date(Date.now() + 60000); current.setSeconds(0, 0);
    var later = new Date(current.getTime() + 8 * 60 * 60 * 1000);
    function localValue(date) { var shifted = new Date(date.getTime() - date.getTimezoneOffset() * 60000); return shifted.toISOString().slice(0, 16); }
    overlay.innerHTML = '<form class="work-reason-dialog glass"><h2>Период официального отсутствия</h2><p>Укажите дату и время начала и окончания.</p><label class="official-period-field">Начало<input type="datetime-local" name="starts_at" required></label><label class="official-period-field">Окончание<input type="datetime-local" name="ends_at" required></label><div class="work-reason-actions"><button type="button" class="button secondary-link" data-period-cancel>Отмена</button><button type="submit" class="button">Подтверждаю</button></div></form>';
    document.body.appendChild(overlay);
    var form = overlay.querySelector("form");
    var start = form.elements.starts_at; var end = form.elements.ends_at;
    start.min = localValue(new Date()); start.value = localValue(current); end.min = start.value; end.value = localValue(later);
    start.addEventListener("change", function () { end.min = start.value; if (end.value <= start.value) { var next = new Date(new Date(start.value).getTime() + 8 * 60 * 60 * 1000); end.value = localValue(next); } });
    function close() { overlay.remove(); }
    overlay.querySelector("[data-period-cancel]").onclick = close;
    overlay.addEventListener("click", function (event) { if (event.target === overlay) close(); });
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      if (new Date(start.value).getTime() < Date.now() - 60000) { start.setCustomValidity("Начало не может быть в прошлом."); start.reportValidity(); return; }
      if (new Date(end.value) <= new Date(start.value)) { end.setCustomValidity("Окончание должно быть позже начала."); end.reportValidity(); return; }
      close(); requestWorkState(button, state, "", { starts_at: start.value, ends_at: end.value });
    });
  }

  menu.querySelectorAll("[data-work-state]").forEach(function (button) {
    button.addEventListener("click", function () {
      var state = button.getAttribute("data-work-state");
      if (state === "other") { requestOtherReason(button); return; }
      if (["vacation", "sick_leave", "business_trip", "day_off"].indexOf(state) !== -1) { requestOfficialPeriod(button, state); return; }
      requestWorkState(button, state, "", {});
    });
  });
  refreshWorkState();
  window.setInterval(refreshWorkState, 20000);
}());
