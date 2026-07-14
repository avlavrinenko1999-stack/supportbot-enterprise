from pathlib import Path


SERVICE_PATH = Path(
    "app/services/account_admin_service.py"
)


def test_pending_invite_lookup_uses_business_unit() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    start = source.index(
        "async def get_pending_invite("
    )
    end = source.index(
        "async def revoke_pending_invite(",
        start,
    )
    block = source[start:end]

    assert "company_id: int" in block
    assert "LegacyCompanyMapping" in block
    assert "organizational_unit_id" in block
    assert "Invite.organizational_unit_id" in block
    assert "Invite.company_id" not in block


def test_pending_invite_lookup_keeps_filters() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    start = source.index(
        "async def get_pending_invite("
    )
    end = source.index(
        "async def revoke_pending_invite(",
        start,
    )
    block = source[start:end]

    assert "Invite.role == invite_role" in block
    assert "Invite.full_name == full_name" in block
    assert "Invite.used_at.is_(None)" in block
    assert "Invite.is_active.is_(True)" in block
    assert "Invite.id.desc()" in block
