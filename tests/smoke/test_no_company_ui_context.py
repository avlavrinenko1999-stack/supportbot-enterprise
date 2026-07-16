from pathlib import Path


CONTEXT_PATH = Path("app/ui/context.py")
CARD_PATH = Path(
    "app/handlers/admin/company/card.py"
)
RESOLVER_PATH = Path(
    "app/security/scope_resolvers.py"
)


def test_ui_context_has_no_legacy_company_id_api() -> None:
    source = CONTEXT_PATH.read_text(encoding="utf-8")

    assert "set_company_id" not in source
    assert "get_company_id" not in source
    assert '"company_id"' not in source


def test_business_unit_card_does_not_write_company_context() -> None:
    source = CARD_PATH.read_text(encoding="utf-8")

    assert "UIContext.set_company_id" not in source
    assert "legacy_company_id =" not in source


def test_scope_resolvers_have_no_company_state_resolver() -> None:
    source = RESOLVER_PATH.read_text(encoding="utf-8")

    assert "company_scope_from_state" not in source
    assert "UIContext.get_company_id" not in source
