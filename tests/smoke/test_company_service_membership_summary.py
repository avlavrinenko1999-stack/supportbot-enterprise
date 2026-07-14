import ast
from pathlib import Path


SERVICE_PATH = Path(
    "app/services/company_service.py"
)


def _summary_method(
    source: str,
) -> ast.AsyncFunctionDef:
    tree = ast.parse(source)

    candidates = []

    for node in ast.walk(tree):
        if not isinstance(
            node,
            ast.AsyncFunctionDef,
        ):
            continue

        block = ast.get_source_segment(
            source,
            node,
        )

        if block is None:
            continue

        if (
            "coordinators_count" in block
            and "employees_count" in block
            and "tickets_count" in block
        ):
            candidates.append(node)

    assert len(candidates) == 1
    return candidates[0]


def _summary_source(source: str) -> str:
    method = _summary_method(source)
    block = ast.get_source_segment(
        source,
        method,
    )

    assert block is not None
    return block


def test_company_summary_uses_membership() -> None:
    source = SERVICE_PATH.read_text(
        encoding="utf-8"
    )
    block = _summary_source(source)

    assert "LegacyCompanyMapping" in block
    assert (
        "AccountOrganizationalUnitMembership"
        in block
    )
    assert "organizational_unit_id" in block
    assert "is_active" in block


def test_company_summary_keeps_role_counts() -> None:
    source = SERVICE_PATH.read_text(
        encoding="utf-8"
    )
    block = _summary_source(source)

    assert (
        "UserRole.COORDINATOR"
        in block
    )
    assert "UserRole.OPERATOR" in block
    assert "UserRole.OBSERVER" in block
    assert "UserRole.USER" in block
    assert "tickets_count" in block


def test_company_service_has_no_account_company_reads() -> None:
    source = SERVICE_PATH.read_text(
        encoding="utf-8"
    )
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
