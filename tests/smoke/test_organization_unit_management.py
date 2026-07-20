from pathlib import Path

import pytest

from app.models.organizational_unit import OrganizationalUnit
from app.services.organization_unit_service import OrganizationUnitService


def test_organizational_unit_has_recursive_management_fields() -> None:
    columns = OrganizationalUnit.__table__.c

    assert "organization_id" in columns
    assert "description" in columns
    assert "owner_account_id" in columns
    assert OrganizationalUnit.parent.property.back_populates == "children"


def test_unit_name_and_description_validation() -> None:
    assert OrganizationUnitService._validate_name(
        "  Отдел   продаж "
    ) == "Отдел продаж"
    assert OrganizationUnitService._validate_description(
        "  Краткое   описание "
    ) == "Краткое описание"

    with pytest.raises(ValueError):
        OrganizationUnitService._validate_name("A")
    with pytest.raises(ValueError):
        OrganizationUnitService._validate_description(
            "x" * 1001
        )


def test_unit_migration_preserves_existing_tree() -> None:
    source = Path(
        "migrations/versions/"
        "20260720_05_add_organization_unit_management.py"
    ).read_text(encoding="utf-8")

    assert "organization_id" in source
    assert "owner_account_id" in source
    assert "UPDATE organizational_units" in source
    assert "DROP TABLE" not in source
