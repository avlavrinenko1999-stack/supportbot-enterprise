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

```

## 2. Организационная модель

В рабочей модели отсутствует отдельная сущность компании.

- `Tenant` задаёт границу изоляции клиента.
- `LegalEntity` хранит юридические и регистрационные реквизиты.
- `OrganizationalUnit` представляет рабочее подразделение и является областью
  сотрудников, приглашений, категорий, обращений и настроек интерфейса.
- Каждое `OrganizationalUnit` принадлежит `Organization`, может иметь
  вышестоящее подразделение, краткое описание, владельца и произвольное число
  участников. Рекурсивная связь `parent_id` образует дерево подразделений.
- `AccountOrganizationalUnitMembership` хранит принадлежность аккаунтов.
- `ScopeType.BUSINESS_UNIT` используется для назначения ролей подразделения.

Таблицы `companies`, `company_settings`, `company_audit_events` и
`legacy_company_mappings` удалены. Добавлять переходные связи или новые поля
`company_id` запрещено; новые функции должны принимать `business_unit_id`.
