from pathlib import Path


SERVICE_PATH = Path(
    "app/services/account_admin_service.py"
)


def test_reissue_invite_uses_primary_membership() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    start = source.index(
        "async def reissue_invite("
    )
    end = source.index(
        "@staticmethod",
        start,
    )
    block = source[start:end]

    assert (
        "AccountOrganizationalUnitMembership"
        in block
    )
    assert "account_id" in block
    assert "is_primary" in block
    assert "is_active" in block
    assert "self.mapping" in block
    assert "get_legacy_company_id" in block
    assert "organizational_unit_id" in block
    assert "account.company_id" not in block


def test_reissue_invite_keeps_compatibility_flow() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    start = source.index(
        "async def reissue_invite("
    )
    end = source.index(
        "@staticmethod",
        start,
    )
    block = source[start:end]

    assert "self.get_pending_invite(" in block
    assert "self.create_invite(" in block
    assert "company_id=company_id" in block
    assert "AccountInviteResult" in block
