from pathlib import Path

from app.models.invite import Invite


MIGRATION_PATH = Path(
    "migrations/versions/20260714_03_make_invite_company_nullable.py"
)


def test_invite_company_id_is_nullable_legacy_column() -> None:
    column = Invite.__table__.c.company_id

    assert column.nullable is True


def test_invite_company_nullable_migration_contract() -> None:
    source = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision: str = "20260714_03"' in source
    assert 'down_revision: str | None = "20260714_02"' in source
    assert '"company_id"' in source
    assert "nullable=True" in source
    assert "nullable=False" in source
    assert "WHERE company_id IS NULL" in source
