# SupportBot Enterprise — архитектура проекта

## 1. Общая схема

Основной поток обработки пользовательского действия:

```text
Telegram Update
    ↓
Handler
    ↓
Application
    ↓
ScreenResponse
    ↓
ScreenPresenter
    ↓
MessageService
    ↓
Telegram API


