from pathlib import Path

from app.services.invite_service import (
    InviteService,
)


INVITE_SERVICE_PATH = Path("app/services/invite_service.py")

AUTH_SERVICE_PATH = Path("app/services/auth.py")


def test_membership_helper_exists() -> None:
    assert hasattr(
        InviteService,
        "ensure_primary_membership",
    )


def test_membership_helper_uses_business_unit_scope() -> None:
    source = INVITE_SERVICE_PATH.read_text(encoding="utf-8")

    assert "AccountOrganizationalUnitMembership" in source
    assert "organizational_unit_id" in source
    assert "is_primary=True" in source
    assert "is_active=True" in source


def test_invite_service_registration_creates_membership() -> None:
    source = INVITE_SERVICE_PATH.read_text(encoding="utf-8")

    start = source.index("async def register_by_token(")
    block = source[start:]

    assert "ensure_primary_membership" in block
    assert "invite.organizational_unit_id" in block
    assert "invite.used_at = now" in block


def test_legacy_auth_registration_creates_membership() -> None:
    source = AUTH_SERVICE_PATH.read_text(encoding="utf-8")

    assert "InviteService" in source
    assert "ensure_primary_membership" in source
    assert "invite.organizational_unit_id" in source


def test_registration_does_not_read_invite_company() -> None:
    invite_source = INVITE_SERVICE_PATH.read_text(encoding="utf-8")
    auth_source = AUTH_SERVICE_PATH.read_text(encoding="utf-8")

    register_start = invite_source.index("async def register_by_token(")
    register_block = invite_source[register_start:]

    assert "invite.company_id" not in register_block
    assert "invite.company_id" not in auth_source


def test_membership_is_in_same_transaction() -> None:
    source = INVITE_SERVICE_PATH.read_text(encoding="utf-8")

    helper_start = source.index("async def ensure_primary_membership(")
    helper_end = source.index(
        "async def create_invite(",
        helper_start,
    )
    helper = source[helper_start:helper_end]

    assert "session.commit" not in helper
    assert "self.session.flush" in helper
