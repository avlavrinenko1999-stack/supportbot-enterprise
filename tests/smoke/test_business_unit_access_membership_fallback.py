import ast
from pathlib import Path


SERVICE_PATH = Path(
    "app/security/business_unit_access.py"
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


def test_fallback_uses_primary_membership() -> None:
    source = SERVICE_PATH.read_text(
        encoding="utf-8"
    )
    block = _method_source(
        source,
        "_legacy_seed_ids",
    )

    assert (
        "AccountOrganizationalUnitMembership"
        in block
    )
    assert ".account_id" in block
    assert "account.id" in block
    assert ".organizational_unit_id" in block
    assert ".is_primary" in block
    assert ".is_active" in block


def test_fallback_preserves_admin_platform_access() -> None:
    source = SERVICE_PATH.read_text(
        encoding="utf-8"
    )
    block = _method_source(
        source,
        "_legacy_seed_ids",
    )

    assert (
        "account.role == UserRole.ADMIN"
        in block
    )
    assert "return None" in block


def test_fallback_denies_account_without_membership() -> None:
    source = SERVICE_PATH.read_text(
        encoding="utf-8"
    )
    block = _method_source(
        source,
        "_legacy_seed_ids",
    )

    assert "if unit_id is None:" in block
    assert "return set()" in block
    assert "return {unit_id}" in block


def test_business_unit_access_has_no_account_company_reads() -> None:
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


def test_fallback_does_not_use_company_mapping() -> None:
    source = SERVICE_PATH.read_text(
        encoding="utf-8"
    )
    block = _method_source(
        source,
        "_legacy_seed_ids",
    )

    assert "LegacyCompanyMapping" not in block
    assert "Company" not in block
