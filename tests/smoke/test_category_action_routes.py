from pathlib import Path


HANDLER_PATH = Path("app/handlers/admin/company_categories.py")

KEYBOARD_PATH = Path("app/keyboards/company_categories.py")


def test_canonical_category_action_routes_exist() -> None:
    source = HANDLER_PATH.read_text(encoding="utf-8")

    actions = {
        "view",
        "create_child",
        "rename",
        "archive_one",
        "restore",
        "delete",
        "delete_confirm",
    }

    for action in actions:
        assert f"business_unit_category:{action}:" in source


def test_legacy_category_action_routes_remain() -> None:
    source = HANDLER_PATH.read_text(encoding="utf-8")

    actions = {
        "view",
        "create_child",
        "rename",
        "archive_one",
        "restore",
        "delete",
        "delete_confirm",
    }

    for action in actions:
        assert f"company_category:{action}:" in source


def test_category_keyboards_use_canonical_actions() -> None:
    source = KEYBOARD_PATH.read_text(encoding="utf-8")

    required_routes = {
        "business_unit_category:view:",
        "business_unit_category:create_child:",
        "business_unit_category:rename:",
        "business_unit_category:archive_one:",
        "business_unit_category:restore:",
        "business_unit_category:delete:",
        "business_unit_category:delete_confirm:",
    }

    for route in required_routes:
        assert route in source


def test_category_card_returns_to_business_unit() -> None:
    source = KEYBOARD_PATH.read_text(encoding="utf-8")

    assert "business_unit:categories:" in source
    assert "business_unit:view:" in source
    assert "category.business_unit_id" in source


def test_category_callback_parsing_is_namespace_independent() -> None:
    source = HANDLER_PATH.read_text(encoding="utf-8")

    assert 'callback.data.rsplit(":", 1)[-1]' in source
