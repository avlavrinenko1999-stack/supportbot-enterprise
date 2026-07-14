import ast
from pathlib import Path


SERVICE_PATH = Path(
    "app/security/company_access.py"
)


def _method_source(
    source: str,
    name: str,
) -> str:
    tree = ast.parse(source)

    method = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(
                node,
                ast.AsyncFunctionDef,
            )
            and node.name == name
        ),
        None,
    )

    assert method is not None

    block = ast.get_source_segment(
        source,
        method,
    )

    assert block is not None
    return block


def test_no_account_company_reads_remain() -> None:
    source = SERVICE_PATH.read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)

    reads = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "account"
        and node.attr == "company_id"
    ]

    assert reads == []


def test_no_assignment_fallback_uses_membership() -> None:
    source = SERVICE_PATH.read_text(
        encoding="utf-8"
    )
    block = _method_source(
        source,
        "_access_condition",
    )

    assert (
        "await self._membership_access_condition("
        in block
    )
    assert "_legacy_access_condition" not in block


def test_membership_condition_preserves_admin_access() -> None:
    source = SERVICE_PATH.read_text(
        encoding="utf-8"
    )
    block = _method_source(
        source,
        "_membership_access_condition",
    )

    assert "account.role == UserRole.ADMIN" in block
    assert "return None" in block
    assert (
        "_primary_membership_company_id("
        in block
    )
    assert "Company.id == company_id" in block


def test_company_lookup_uses_primary_active_membership() -> None:
    source = SERVICE_PATH.read_text(
        encoding="utf-8"
    )
    block = _method_source(
        source,
        "_primary_membership_company_id",
    )

    assert (
        "AccountOrganizationalUnitMembership"
        in block
    )
    assert "LegacyCompanyMapping" in block
    assert ".is_primary" in block
    assert ".is_active" in block
    assert "organizational_unit_id" in block
    assert "account_id" in block
