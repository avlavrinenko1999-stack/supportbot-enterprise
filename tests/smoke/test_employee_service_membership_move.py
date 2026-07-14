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

def test_employee_move_has_no_legacy_company_write() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    move_method = next(
        (
            item
            for item in ast.walk(tree)
            if isinstance(
                item,
                ast.AsyncFunctionDef,
            )
            and item.name == "move_to_company"
        ),
        None,
    )

    assert move_method is not None

    assignments = []

    for item in ast.walk(move_method):
        if not isinstance(
            item,
            (ast.Assign, ast.AnnAssign),
        ):
            continue

        targets = (
            item.targets
            if isinstance(item, ast.Assign)
            else [item.target]
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
                assignments.append(
                    item.lineno
                )

    assert assignments == []
