from app.handlers.admin.access import (
    AccessAssignmentState,
    _parse_revoke_button,
    access_audit,
    access_revoke_confirm,
)
from app.models import AccessAuditEvent, Base
from app.ui.actions import MenuAction, resolve_menu_action


def test_access_audit_table_is_registered() -> None:
    assert "access_audit_events" in Base.metadata.tables
    assert AccessAuditEvent.__tablename__ == "access_audit_events"


def test_revoke_actions_are_registered() -> None:
    assert (
        resolve_menu_action("✅ Подтвердить отзыв")
        == MenuAction.ACCESS_REVOKE_CONFIRM
    )
    assert (
        resolve_menu_action("❌ Отменить отзыв")
        == MenuAction.ACCESS_REVOKE_CANCEL
    )


def test_revoke_button_parser() -> None:
    assert _parse_revoke_button("❌ Отозвать #15") == 15
    assert _parse_revoke_button("❌ Отозвать #0") is None
    assert _parse_revoke_button("Отозвать #15") is None
    assert _parse_revoke_button("❌ Отозвать #abc") is None


def test_revoke_state_and_handlers_exist() -> None:
    assert (
        AccessAssignmentState.revoke_confirmation.state
        == "AccessAssignmentState:revoke_confirmation"
    )
    assert callable(access_revoke_confirm)
    assert callable(access_audit)
