(function () {
  "use strict";
  var storageKey = "supportbot-app-build";
  var ignoredKey = "supportbot-ignored-build";

  function showNotice(version) {
    if (document.getElementById("supportbot-update-notice")) return;
    var overlay = document.createElement("div");
    overlay.id = "supportbot-update-notice";
    overlay.className = "update-notice-overlay";
    overlay.innerHTML = '<section class="update-notice glass" role="dialog" aria-modal="true" aria-labelledby="update-notice-title">' +
      '<div class="update-notice-icon" aria-hidden="true">✦</div>' +
      '<h2 id="update-notice-title">Обновление функционала</h2>' +
      '<p>В функционале появились обновления от разработчика. Перезагрузить сервис?</p>' +
      '<div class="update-notice-actions"><button type="button" data-update-yes>Да</button><button type="button" class="secondary" data-update-no>Нет</button></div></section>';
    document.body.appendChild(overlay);
    overlay.querySelector("[data-update-yes]").onclick = function () {
      try { localStorage.setItem(storageKey, version); } catch (e) {}
      window.location.reload();
    };
    overlay.querySelector("[data-update-no]").onclick = function () {
      try { localStorage.setItem(ignoredKey, version); } catch (e) {}
      overlay.parentNode.removeChild(overlay);
    };
  }

  function checkVersion() {
    var request = new XMLHttpRequest();
    request.open("GET", "/api/version?_=" + new Date().getTime(), true);
    request.onreadystatechange = function () {
      if (request.readyState !== 4 || request.status !== 200) return;
      try {
        var version = JSON.parse(request.responseText).version;
        var current = localStorage.getItem(storageKey);
        var ignored = localStorage.getItem(ignoredKey);
        if (!current) localStorage.setItem(storageKey, version);
        else if (current !== version && ignored !== version) showNotice(version);
      } catch (e) {}
    };
    request.send();
  }

  checkVersion();
  window.setInterval(checkVersion, 30000);
}());
