import inspect
from pathlib import Path

from app.repositories.user import create_account
from app.services.invite_service import (
    InviteService,
)


INVITE_SERVICE = Path("app/services/invite_service.py")
AUTH_SERVICE = Path("app/services/auth.py")
USER_REPOSITORY = Path("app/repositories/user.py")


def test_create_account_has_no_company_parameter() -> None:
    signature = inspect.signature(create_account)

    assert "company_id" not in signature.parameters


def test_account_repository_does_not_assign_company() -> None:
    source = USER_REPOSITORY.read_text(encoding="utf-8")

    assert "company_id" not in source
    assert "Account(" in source


def test_invite_service_registration_is_business_unit_first() -> None:
    source = INVITE_SERVICE.read_text(encoding="utf-8")

    start = source.index("async def register_by_token(")
    block = source[start:]

    assert "invite.company_id" not in block
    assert "invite.organizational_unit_id" in block
    assert "ensure_primary_membership" in block


def test_legacy_auth_registration_is_business_unit_first() -> None:
    source = AUTH_SERVICE.read_text(encoding="utf-8")

    assert "invite.company_id" not in source
    assert "invite.organizational_unit_id" in source
    assert "ensure_primary_membership" in source


def test_invite_company_bridge_is_creation_only() -> None:
    source = INVITE_SERVICE.read_text(encoding="utf-8")

    create_start = source.index("async def create_invite(")
    register_start = source.index("async def register_by_token(")

    creation_block = source[create_start:register_start]
    registration_block = source[register_start:]

    assert "company_id" in creation_block
    assert "invite.company_id" not in registration_block


def test_registration_helpers_remain_available() -> None:
    assert hasattr(
        InviteService,
        "register_by_token",
    )
    assert hasattr(
        InviteService,
        "ensure_primary_membership",
    )
