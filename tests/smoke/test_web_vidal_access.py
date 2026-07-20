from pathlib import Path


APPLICATION = (
    Path(__file__).resolve().parents[2] / "web" / "application.py"
).read_text(encoding="utf-8")


def test_vidal_routes_are_registered() -> None:
    assert 'add_get("/vidal", vidal_page)' in APPLICATION
    assert 'add_get("/vidal/search", vidal_search)' in APPLICATION
    assert "Справочник Vidal" in APPLICATION


def test_vidal_requires_exact_platform_administrator_role() -> None:
    assert "async def is_platform_admin" in APPLICATION
    assert 'Role.code == "platform_admin"' in APPLICATION
    assert "RoleAssignment.scope_type == ScopeType.PLATFORM" in APPLICATION
    assert APPLICATION.count("if not await require_platform_admin(account)") >= 2


def test_vidal_search_uses_official_directory() -> None:
    assert "results = await VidalService.search(query)" in APPLICATION
    assert "Официальная карточка Vidal" in APPLICATION
    assert 'target="_blank" rel="noopener noreferrer"' in APPLICATION
    assert "Информация предназначена для специалистов" in APPLICATION
