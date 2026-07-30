(function () {
  "use strict";
  var cfg = window.supportBotAgentConfig;
  if (!cfg || !cfg.enabled) return;
  var local = "http://127.0.0.1:47831";
  var pendingKey = "supportbot-agent-install-pending:" + cfg.agentVersion;
  var knownInstallKey = "supportbot-agent-install-known";

  function hasPriorInstall() {
    if (localStorage.getItem(knownInstallKey) === "1" || cfg.serverSeenVersion) return true;
    for (var i = 0; i < localStorage.length; i += 1) {
      var key = localStorage.key(i) || "";
      if (key.indexOf("supportbot-agent-install-pending:") === 0) return true;
    }
    return false;
  }

  function pendingActive() {
    var started = Number(localStorage.getItem(pendingKey) || 0);
    return started > 0 && Date.now() - started < 30 * 60 * 1000;
  }
  function showPendingNotice() {
    if (document.querySelector(".agent-install-pending")) return;
    var notice = document.createElement("div");
    notice.className = "agent-install-pending glass";
    notice.textContent = "Файл агента загружен. Завершите установку — подключение произойдёт автоматически.";
    document.body.appendChild(notice);
    window.setTimeout(function () { notice.remove(); }, 9000);
  }

  function probe() {
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, 900);
    return fetch(local + "/status", { cache: "no-store", signal: controller.signal })
      .then(function (r) { clearTimeout(timer); return r.ok ? r.json() : Promise.reject(); });
  }
  function enroll() {
    return fetch(local + "/enroll", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ server_url: cfg.serverUrl, token: cfg.token })
    });
  }
  function pollForAgent() {
    probe().then(function (status) {
      if (status.version !== cfg.agentVersion) return Promise.reject();
      return enroll();
    }).then(function () {
      localStorage.setItem(knownInstallKey, "1");
      localStorage.removeItem(pendingKey);
      localStorage.removeItem(declineKey);
    }).catch(function () { if (pendingActive()) window.setTimeout(pollForAgent, 2500); });
  }
  var declineKey = "supportbot-agent-update-declined:" + cfg.agentVersion;
  function showDeclinedWarning() {
    if (document.querySelector(".agent-update-declined")) return;
    var warning = document.createElement("div");
    warning.className = "agent-update-declined glass";
    warning.textContent = "Установка обновления агента отклонена, часть функционала может работать некорректно";
    document.body.appendChild(warning);
  }
  function modal(update) {
    var offeredKey = "supportbot-agent-offered:" + cfg.agentVersion + ":" + (update ? "update" : "install");
    if (sessionStorage.getItem(offeredKey) === "1") return;
    sessionStorage.setItem(offeredKey, "1");
    var mac = /Mac/.test(navigator.platform);
    var download = mac ? cfg.macDownload : cfg.windowsDownload;
    var overlay = document.createElement("div");
    overlay.className = "agent-offer-overlay";
    overlay.innerHTML = '<section class="agent-offer glass ' + (update ? "agent-offer-update" : "") + '"><span class="agent-offer-kicker">' + (update ? "Обновление агента" : "Тестовая версия") + '</span><h2>' + (update ? "Доступна новая версия" : "Подключить учет активности?") + '</h2>' + (update ? '<div class="agent-version-row"><span>Установленная версия</span><b>' + (cfg.serverSeenVersion || "предыдущая") + '</b><span class="agent-version-arrow">→</span><span>Новая версия</span><b>' + cfg.agentVersion + '</b></div>' : '') + '<p>' + (update ? "Обновите SupportBot Presence, чтобы статусы, уведомления и учет рабочего времени продолжали работать корректно." : "Агент определяет только время системного простоя, блокировку ПК и доступность устройства. Названия приложений, тексты, клавиши и снимки экрана не собираются.") + '</p><p class="agent-offer-warning">Скачивается один установочный файл. Сборка пока не подписана и предназначена для тестирования.</p><div class="agent-offer-actions"><a class="button" href="' + download + '" download>' + (update ? "Установить обновление" : "Установить") + ' для ' + (mac ? "macOS" : "Windows") + '</a><button class="button secondary-link" type="button" data-agent-later>' + (update ? "Отклонить обновление" : "Позже") + '</button></div></section>';
    document.body.appendChild(overlay);
    overlay.querySelector("[data-agent-later]").onclick = function () {
      overlay.remove();
      if (update) { localStorage.setItem(declineKey, "1"); showDeclinedWarning(); }
    };
    overlay.querySelector("a").onclick = function () {
      if (mac && !overlay.querySelector(".agent-macos-help")) {
        overlay.querySelector(".agent-offer-actions").insertAdjacentHTML("beforebegin", '<div class="agent-macos-help"><b>Если macOS заблокирует пакет:</b><ol><li>Нажмите «Готово» в системном предупреждении.</li><li>Откройте «Системные настройки» → «Конфиденциальность и безопасность».</li><li>Внизу страницы нажмите «Всё равно открыть» и подтвердите пароль Mac.</li></ol><a href="x-apple.systempreferences:com.apple.preference.security?Privacy" class="agent-settings-link">Открыть настройки безопасности</a></div>');
      }
      localStorage.setItem(pendingKey, String(Date.now()));
      localStorage.setItem(knownInstallKey, "1");
      overlay.remove();
      showPendingNotice();
      window.setTimeout(pollForAgent, 2500);
    };
  }
  if (localStorage.getItem(declineKey) === "1") showDeclinedWarning();
  probe().then(function (status) {
    localStorage.setItem(knownInstallKey, "1");
    if (status.version !== cfg.agentVersion) { if (pendingActive()) { showPendingNotice(); pollForAgent(); } else { modal(true); } return; }
    localStorage.removeItem(pendingKey);
    localStorage.removeItem(declineKey);
    return enroll();
  }).catch(function () {
    if (pendingActive()) { showPendingNotice(); pollForAgent(); return; }
    modal(hasPriorInstall() && (!cfg.serverSeenVersion || cfg.serverSeenVersion !== cfg.agentVersion));
  });
}());
