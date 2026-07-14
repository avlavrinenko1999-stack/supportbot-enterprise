from pathlib import Path

from app.handlers.admin.company_coordinators import (
    business_unit_coordinator_create_finish,
    business_unit_coordinator_create_start,
    business_unit_coordinator_disable,
    business_unit_coordinator_enable,
    business_unit_coordinator_view,
    business_unit_coordinators,
)
from app.keyboards.company_coordinators import (
    back_to_business_unit_coordinators_menu,
    business_unit_coordinator_card_menu,
    business_unit_coordinators_menu,
)


HANDLER = Path("app/handlers/admin/company_coordinators.py")

KEYBOARD = Path("app/keyboards/company_coordinators.py")

CARD_KEYBOARD = Path("app/keyboards/company.py")


def test_canonical_handlers_exist() -> None:
    functions = [
        business_unit_coordinators,
        business_unit_coordinator_create_start,
        business_unit_coordinator_create_finish,
        business_unit_coordinator_view,
        business_unit_coordinator_disable,
        business_unit_coordinator_enable,
    ]

    for function in functions:
        assert callable(function)


def test_canonical_keyboards_exist() -> None:
    functions = [
        business_unit_coordinators_menu,
        business_unit_coordinator_card_menu,
        back_to_business_unit_coordinators_menu,
    ]

    for function in functions:
        assert callable(function)


def test_handler_uses_new_service() -> None:
    source = HANDLER.read_text(encoding="utf-8")

    assert "BusinessUnitCoordinatorService" in source
    assert "business_unit:coordinators:" in source
    assert "business_unit_coordinator:" in source


def test_handlers_are_membership_scoped() -> None:
    source = HANDLER.read_text(encoding="utf-8")

    assert "set_membership_active" in source
    assert "get_coordinator" in source
    assert "list_coordinators" in source
    assert "business_unit_coordinator_unit_id" in source


def test_keyboard_uses_business_unit_routes() -> None:
    source = KEYBOARD.read_text(encoding="utf-8")

    assert "business_unit:coordinators:" in source
    assert "business_unit_coordinator:" in source
    assert "view:" in source
    assert "create:" in source
    assert "business_unit:view:" in source


def test_business_unit_card_uses_route() -> None:
    source = CARD_KEYBOARD.read_text(encoding="utf-8")

    assert "business_unit:coordinators:" in source
    assert "Координаторы подразделения" in source


def test_legacy_routes_remain_available() -> None:
    source = HANDLER.read_text(encoding="utf-8")

    assert "company:coordinators:" in source
    assert "company_coordinator:create:" in source
    assert "CompanyService" in source
