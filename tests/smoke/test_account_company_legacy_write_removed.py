import ast
from pathlib import Path


APP_PATH = Path("app")


def test_production_has_no_account_company_reads_or_writes() -> None:
    violations: list[str] = []

    for path in sorted(APP_PATH.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Attribute):
                continue

            if node.attr != "company_id":
                continue

            if not isinstance(node.value, ast.Name):
                continue

            if node.value.id not in {
                "Account",
                "account",
            }:
                continue

            violations.append(
                f"{path}:{node.lineno}:"
                f"{node.value.id}.company_id"
            )

    assert violations == []


def test_employee_move_remains_membership_canonical() -> None:
    path = Path(
        "app/services/employee_service.py"
    )
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    method = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(
                node,
                ast.AsyncFunctionDef,
            )
            and node.name == "move_to_company"
        ),
        None,
    )

    assert method is not None

    block = ast.get_source_segment(
        source,
        method,
    )

    assert block is not None
    assert (
        "AccountOrganizationalUnitMembership"
        in block
    )
    assert "with_for_update()" in block
    assert "is_primary" in block
    assert "is_active" in block
    assert "account.company_id" not in block
