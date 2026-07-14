from pathlib import Path


SERVICE_PATH = Path(
    "app/services/account_admin_service.py"
)


def test_company_account_listing_uses_membership() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    start = source.index(
        "async def list_company_accounts("
    )
    end = source.index(
        "async def get_account(",
        start,
    )
    block = source[start:end]

    assert "company_id: int" in block
    assert "LegacyCompanyMapping" in block
    assert (
        "AccountOrganizationalUnitMembership"
        in block
    )
    assert "organizational_unit_id" in block
    assert "is_active" in block
    assert "Account.company_id" not in block


def test_company_account_listing_keeps_compatibility_contract() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    start = source.index(
        "async def list_company_accounts("
    )
    end = source.index(
        "async def get_account(",
        start,
    )
    block = source[start:end]

    assert "company_id: int" in block
    assert "role: UserRole" in block
    assert "-> list[Account]" in block
