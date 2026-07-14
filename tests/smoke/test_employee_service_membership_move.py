import ast
from pathlib import Path


SERVICE_PATH = Path(
    "app/services/employee_service.py"
)


def _move_method_block(source: str) -> str:
    start = source.index(
        "async def move_to_company("
    )
    end = source.index(
        "async def count_by_company(",
        start,
    )
    return source[start:end]


def test_employee_move_uses_membership() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")
    block = _move_method_block(source)

    assert (
        "AccountOrganizationalUnitMembership"
        in block
    )
    assert "_get_business_unit_id(" in block
    assert "with_for_update()" in block
    assert "organizational_unit_id" in block
    assert "is_primary" in block
    assert "is_active" in block


def test_employee_move_deactivates_old_primary() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")
    block = _move_method_block(source)

    assert "membership.is_primary = False" in block
    assert "membership.is_active = False" in block
    assert "await self.session.flush()" in block


def test_employee_move_reuses_existing_membership() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")
    block = _move_method_block(source)

    assert "target_membership = next(" in block
    assert "if target_membership is None:" in block
    assert (
        "AccountOrganizationalUnitMembership("
        in block
    )
    assert "target_membership.is_active = True" in block
    assert "target_membership.is_primary = True" in block


def test_employee_move_keeps_legacy_sync_only() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    move_method = next(
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

    assert move_method is not None

    account_company_reads = [
        node.lineno
        for node in ast.walk(move_method)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "Account"
        and node.attr == "company_id"
    ]

    legacy_assignments = []

    for node in ast.walk(move_method):
        if not isinstance(
            node,
            (ast.Assign, ast.AnnAssign),
        ):
            continue

        targets = (
            node.targets
            if isinstance(node, ast.Assign)
            else [node.target]
        )

        for target in targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(
                    target.value,
                    ast.Name,
                )
                and target.value.id == "account"
                and target.attr == "company_id"
            ):
                legacy_assignments.append(
                    node.lineno
                )

    assert account_company_reads == []
    assert len(legacy_assignments) == 1
