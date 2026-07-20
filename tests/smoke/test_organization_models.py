from sqlalchemy import inspect

from app.models import Base, Holding, Organization
from app.models.enums import OrganizationType


def test_organization_models_are_registered() -> None:
    table_names = set(Base.metadata.tables)

    assert "organizations" in table_names
    assert "holdings" in table_names
    assert "companies" not in table_names


def test_organization_type_values_are_stable() -> None:
    assert OrganizationType.PLATFORM.value == "platform"
    assert OrganizationType.CUSTOMER.value == "customer"
    assert (
        OrganizationType.SUPPORT_PROVIDER.value
        == "support_provider"
    )
    assert OrganizationType.PARTNER.value == "partner"


def test_organization_table_structure() -> None:
    table = inspect(Organization).local_table

    assert {
        "id",
        "name",
        "organization_type",
        "parent_id",
        "is_active",
        "created_at",
        "updated_at",
    }.issubset(table.columns.keys())

    assert table.c.parent_id.nullable is True
    assert table.c.is_active.nullable is False


def test_holding_table_structure() -> None:
    table = inspect(Holding).local_table

    assert {
        "id",
        "organization_id",
        "name",
        "is_active",
        "created_at",
        "updated_at",
    }.issubset(table.columns.keys())

    assert table.c.organization_id.nullable is False


def test_account_role_model_uses_membership_scope() -> None:
    account_table = Base.metadata.tables["accounts"]

    assert "role" in account_table.columns
    assert "company_id" not in account_table.columns
    assert (
        "account_organizational_unit_memberships"
        in Base.metadata.tables
    )
