from pathlib import Path


SERVICE_PATH = Path("app/services/employee_service.py")


def _method_block(
    source: str,
    start_marker: str,
    end_marker: str,
) -> str:
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[start:end]


def test_employee_company_listing_uses_membership() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    block = _method_block(
        source,
        "async def list_by_company(",
        "async def list_by_company_and_role(",
    )

    assert "_get_business_unit_id(" in block
    assert "_membership_account_statement(" in block
    assert "Account.company_id" not in block


def test_employee_role_listing_uses_membership() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    block = _method_block(
        source,
        "async def list_by_company_and_role(",
        "async def search(",
    )

    assert "_get_business_unit_id(" in block
    assert "_membership_account_statement(" in block
    assert "Account.role == role" in block
    assert "Account.company_id" not in block


def test_employee_search_company_filter_uses_membership() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    block = _method_block(
        source,
        "async def search(",
        "async def activate(",
    )

    assert "LegacyCompanyMapping" not in block
    assert "_get_business_unit_id(" in block
    assert (
        "AccountOrganizationalUnitMembership"
        in block
    )
    assert "Account.company_id" not in block


def test_employee_count_uses_membership() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    block = source[
        source.index("async def count_by_company("):
    ]

    assert "_get_business_unit_id(" in block
    assert (
        "AccountOrganizationalUnitMembership"
        in block
    )
    assert "Account.company_id" not in block

def test_employee_service_has_no_account_company_writes() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert "account.company_id =" not in source
    assert "Account.company_id =" not in source
    assert "async def move_to_company(" in source
