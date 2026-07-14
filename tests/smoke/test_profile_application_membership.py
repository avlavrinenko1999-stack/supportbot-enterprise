import ast
from pathlib import Path


APPLICATION_PATH = Path(
    "app/application/profile_application.py"
)


def _build_profile_method(
    source: str,
) -> ast.AsyncFunctionDef:
    tree = ast.parse(source)

    method = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(
                node,
                ast.AsyncFunctionDef,
            )
            and node.name == "build_profile"
        ),
        None,
    )

    assert method is not None
    return method


def _build_profile_source(source: str) -> str:
    method = _build_profile_method(source)
    block = ast.get_source_segment(
        source,
        method,
    )

    assert block is not None
    return block


def test_profile_uses_primary_membership() -> None:
    source = APPLICATION_PATH.read_text(
        encoding="utf-8"
    )
    block = _build_profile_source(source)

    assert (
        "AccountOrganizationalUnitMembership"
        in block
    )
    assert "OrganizationalUnit" in block
    assert ".is_primary" in block
    assert ".is_active" in block
    assert "account.id" in block


def test_profile_displays_business_unit() -> None:
    source = APPLICATION_PATH.read_text(
        encoding="utf-8"
    )
    block = _build_profile_source(source)

    assert (
        '"Рабочее подразделение: "'
        in block
    )
    assert "business_unit.name" in block
    assert "business_unit.id" in block
    assert '"Компания: "' not in block


def test_profile_has_no_account_company_reads() -> None:
    source = APPLICATION_PATH.read_text(
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


def test_profile_does_not_query_company() -> None:
    source = APPLICATION_PATH.read_text(
        encoding="utf-8"
    )

    assert (
        "from app.models.company import Company"
        not in source
    )
    assert "select(Company)" not in source
