import ast
from pathlib import Path


SERVICE_PATH = Path(
    "app/services/category_member_service.py"
)


def _method(
    source: str,
    name: str,
) -> ast.AsyncFunctionDef:
    tree = ast.parse(source)

    method = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.AsyncFunctionDef)
            and node.name == name
        ),
        None,
    )

    assert method is not None
    return method


def _method_source(
    source: str,
    name: str,
) -> str:
    method = _method(source, name)
    block = ast.get_source_segment(source, method)

    assert block is not None
    return block


def test_available_accounts_use_membership() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")
    block = _method_source(
        source,
        "list_available_company_accounts",
    )

    assert "company_id: int" in block
    assert "_get_business_unit_id(" in block
    assert (
        "AccountOrganizationalUnitMembership"
        in block
    )
    assert "organizational_unit_id" in block
    assert "is_active" in block
    assert "Account.company_id" not in block


def test_add_member_uses_category_business_unit() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")
    block = _method_source(source, "add_member")

    assert (
        "AccountOrganizationalUnitMembership"
        in block
    )
    assert "category.business_unit_id" in block
    assert "Account.company_id" not in block
    assert "category.company_id" not in block


def test_category_member_service_has_no_account_company_reads() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    reads = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "Account"
        and node.attr == "company_id"
    ]

    assert reads == []


def test_company_contract_is_compatibility_only() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")
    block = _method_source(
        source,
        "list_available_company_accounts",
    )

    assert "company_id: int" in block
    assert "LegacyCompanyMapping" not in block
    assert "_get_business_unit_id(" in block

    helper = _method_source(
        source,
        "_get_business_unit_id",
    )

    assert "self.mapping" in helper
    assert (
        "get_unit_id_by_legacy_company_id"
        in helper
    )
    assert "LegacyCompanyMapping." not in helper
