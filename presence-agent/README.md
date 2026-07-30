# SupportBot Presence Agent

Исходный код тестового агента учёта присутствия для macOS и Windows.

Текущая версия протокола агента задаётся переменной `version` в `main.go`.

## Состав

- `main.go` — локальный API, регистрация, heartbeat и рабочие статусы.
- `presence_darwin.go` — определение простоя и уведомления macOS.
- `presence_windows.go` — установка, системное меню и определение простоя Windows.
- `StatusMenu.m` — системное меню macOS.
- `install-macos.command` и `install-windows.cmd` — тестовые установочные сценарии.

Собранные тестовые установщики, используемые сайтом, находятся в
`web/static/agents/`.

Перед выпуском production-версии сборки должны быть подписаны сертификатами
Apple Developer ID и Microsoft Authenticode.
