from sqlalchemy import inspect

from app.models import (
    Account,
    AccountOrganizationalUnitMembership,
    Base,
    LegalEntity,
    OrganizationalUnit,
    Tenant,
)
from app.models.enums import OrganizationalUnitType


def test_enterprise_tables_are_registered() -> None:
    tables = Base.metadata.tables

    assert "tenants" in tables
    assert "legal_entities" in tables
    assert "organizational_units" in tables
    assert (
        "account_organizational_unit_memberships"
        in tables
    )


def test_organizational_unit_types_are_complete() -> None:
    assert {
        item.value
        for item in OrganizationalUnitType
    } == {
        "general",
        "business_unit",
        "division",
        "department",
        "branch",
        "office",
        "plant",
        "warehouse",
        "service_center",
        "cost_center",
        "region",
        "project_office",
    }


def test_legal_entity_contains_only_legal_data() -> None:
    table = inspect(LegalEntity).local_table

    assert {
        "tenant_id",
        "name",
        "legal_name",
        "inn",
        "kpp",
        "ogrn",
        "legal_address",
        "legal_status",
        "legal_status_code",
        "registration_date",
        "liquidation_date",
        "phone",
        "last_registry_sync_at",
        "is_active",
    }.issubset(table.columns.keys())

    assert "account_id" not in table.columns
    assert "ticket_id" not in table.columns


def test_organizational_unit_has_strict_ownership() -> None:
    table = inspect(
        OrganizationalUnit
    ).local_table

    assert table.c.tenant_id.nullable is False
    assert table.c.legal_entity_id.nullable is False
    assert table.c.parent_id.nullable is True
    assert table.c.unit_type.nullable is False


def test_membership_connects_account_and_unit() -> None:
    table = inspect(
        AccountOrganizationalUnitMembership
    ).local_table

    assert table.c.account_id.nullable is False
    assert (
        table.c.organizational_unit_id.nullable
        is False
    )
    assert table.c.is_primary.nullable is False
    assert table.c.is_active.nullable is False


def test_account_exposes_unit_memberships() -> None:
    relationships = inspect(Account).relationships

    assert (
        "organizational_unit_memberships"
        in relationships
    )


def test_domain_relationships_are_registered() -> None:
    tenant_relationships = inspect(
        Tenant
    ).relationships
    legal_relationships = inspect(
        LegalEntity
    ).relationships
    unit_relationships = inspect(
        OrganizationalUnit
    ).relationships

    assert "legal_entities" in tenant_relationships
    assert (
        "organizational_units"
        in tenant_relationships
    )
    assert (
        "organizational_units"
        in legal_relationships
    )
    assert "parent" in unit_relationships
    assert "children" in unit_relationships
    assert (
        "account_memberships"
        in unit_relationships
    )


def test_legacy_company_domain_still_exists() -> None:
    tables = Base.metadata.tables

    assert "companies" in tables
    assert "company_id" in tables["accounts"].columns
    assert "company_id" in tables["tickets"].columns
    assert "company_id" in tables["categories"].columns
