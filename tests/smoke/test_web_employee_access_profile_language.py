from pathlib import Path


APPLICATION = (
    Path(__file__).resolve().parents[2] / "web" / "application.py"
).read_text(encoding="utf-8")


def test_employee_web_navigation_matches_bot_sections() -> None:
    for label in (
        "Все сотрудники",
        "Координаторы",
        "Операторы",
        "Наблюдатели",
        "Пользователи",
        "🔎 Найти сотрудника",
        "➕ Создать приглашение",
    ):
        assert label in APPLICATION


def test_access_web_has_assignment_catalog_and_audit() -> None:
    for label in (
        "➕ Назначить роль",
        "📋 Активные назначения",
        "🕘 История назначений",
        "🛡 Роли",
        "🔑 Разрешения",
        "📜 Журнал доступа",
    ):
        assert label in APPLICATION
    assert "RoleGrantPolicy" in APPLICATION
    assert "RoleAssignmentService" in APPLICATION
    assert "AccessAuditAccessService" in APPLICATION


def test_access_mutations_are_scope_and_csrf_protected() -> None:
    assert 'add_post("/access/assign"' in APPLICATION
    assert 'add_post("/access/assignments/{id:\\\\d+}/revoke"' in APPLICATION
    assert "valid_csrf(request, form)" in APPLICATION
    assert "scope=scope" in APPLICATION


def test_profile_exposes_permissions_like_telegram() -> None:
    assert "role_permissions(account.role)" in APPLICATION
    assert "get_permission_name(permission)" in APPLICATION
    assert "<h3>Разрешения</h3>" in APPLICATION


def test_language_uses_dynamic_language_pack_flow() -> None:
    assert "LanguagePackService.resolve_language(query)" in APPLICATION
    assert "LanguagePackService.install_language_pack(query)" in APPLICATION
    assert "installed_languages()" in APPLICATION
    assert "Type your language" in APPLICATION
