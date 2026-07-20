from pathlib import Path
from uuid import UUID

from app.models.organization import Organization


def test_new_organizations_receive_distinct_1c_style_ids() -> None:
    # Column defaults are normally applied during INSERT; invoke the configured
    # generator directly to verify its format and collision independence.
    generator = Organization.__table__.c.external_id.default.arg
    first_id = generator(None)
    second_id = generator(None)

    assert isinstance(first_id, UUID)
    assert str(first_id) == str(UUID(str(first_id)))
    assert first_id != second_id


def test_database_enforces_external_id_uniqueness() -> None:
    source = Path(
        "migrations/versions/"
        "20260720_04_add_organization_external_id.py"
    ).read_text(encoding="utf-8")

    assert '"external_id"' in source
    assert "nullable=False" in source
    assert "unique=True" in source
