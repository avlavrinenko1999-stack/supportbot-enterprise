import ast
from pathlib import Path


HANDLER_PATH = Path(
    "app/handlers/admin/employees.py"
)


def _function_source(
    source: str,
    name: str,
) -> str:
    tree = ast.parse(source)

    function = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
            and node.name == name
        ),
        None,
    )

    assert function is not None

    block = ast.get_source_segment(
        source,
        function,
    )

    assert block is not None
    return block


def test_account_statement_uses_primary_membership() -> None:
    source = HANDLER_PATH.read_text(
        encoding="utf-8"
    )
    block = _function_source(
        source,
        "_account_list_statement",
    )

    assert (
        "AccountOrganizationalUnitMembership"
        in block
    )
    assert "OrganizationalUnit.name" in block
    assert "OrganizationalUnit.id" in block
    assert ".is_primary" in block
    assert ".is_active" in block
    assert ".outerjoin(" in block


def test_account_line_displays_business_unit() -> None:
    source = HANDLER_PATH.read_text(
        encoding="utf-8"
    )
    block = _function_source(
        source,
        "_account_line",
    )

    assert "business_unit_name" in block
    assert "business_unit_id" in block
    assert "подразделение" in block
    assert "без рабочего подразделения" in block
    assert "компания #" not in block


def test_employee_handler_has_no_account_company_reads() -> None:
    source = HANDLER_PATH.read_text(
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


def test_all_employee_queries_use_canonical_statement() -> None:
    source = HANDLER_PATH.read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)

    calls = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id
        == "_account_list_statement"
    ]

    execute_calls = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(
            node.func.value,
            ast.Name,
        )
        and node.func.value.id == "session"
        and node.func.attr == "execute"
    ]

    assert len(calls) == 3
    assert len(execute_calls) == 3
    assert "await session.scalars(" not in source
