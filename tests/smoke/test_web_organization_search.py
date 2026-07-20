from pathlib import Path


APPLICATION = (
    Path(__file__).resolve().parents[2]
    / "web"
    / "application.py"
).read_text(encoding="utf-8")


def test_organization_page_does_not_load_catalog_without_query() -> None:
    empty_guard = APPLICATION.index("if not query:")
    catalog_query = APPLICATION.index(
        "OrganizationAccessService(db).list_visible_organizations(account)",
        empty_guard,
    )

    assert empty_guard < catalog_query


def test_organization_search_is_limited_and_access_scoped() -> None:
    assert "][:8]" in APPLICATION
    assert "ИНН или часть наименования" in APPLICATION
    assert "OrganizationAccessService" in APPLICATION
