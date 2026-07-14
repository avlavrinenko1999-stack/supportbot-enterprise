import ast
from pathlib import Path


MIGRATION_PATH = Path(
    "migrations/versions/"
    "20260714_04_drop_account_company_id.py"
)


def _function_source(
    source: str,
    name: str,
) -> str:
    tree = ast.parse(source)

    function = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
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


def test_migration_revision_chain() -> None:
    source = MIGRATION_PATH.read_text(
        encoding="utf-8"
    )

    assert 'revision: str = "20260714_04"' in source
    assert (
        'down_revision: str | None = "20260714_03"'
        in source
    )


def test_upgrade_drops_fk_before_column() -> None:
    source = MIGRATION_PATH.read_text(
        encoding="utf-8"
    )
    block = _function_source(source, "upgrade")

    constraint_position = block.index(
        "op.drop_constraint("
    )
    column_position = block.index(
        "op.drop_column("
    )

    assert constraint_position < column_position
    assert '"accounts_company_id_fkey"' in block
    assert '"accounts"' in block
    assert 'type_="foreignkey"' in block
    assert '"company_id"' in block


def test_downgrade_restores_nullable_column_and_fk() -> None:
    source = MIGRATION_PATH.read_text(
        encoding="utf-8"
    )
    block = _function_source(source, "downgrade")

    column_position = block.index(
        "op.add_column("
    )
    constraint_position = block.index(
        "op.create_foreign_key("
    )

    assert column_position < constraint_position
    assert "sa.Integer()" in block
    assert "nullable=True" in block
    assert '"accounts_company_id_fkey"' in block
    assert '"companies"' in block
    assert '["company_id"]' in block
    assert '["id"]' in block
