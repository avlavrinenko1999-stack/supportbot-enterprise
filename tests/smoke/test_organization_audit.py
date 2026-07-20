from sqlalchemy import inspect

from app.models import (
    Base,
    Organization,
    OrganizationAuditEvent,
)
from app.security.permission_mapping import (
    permission_codes,
)
from app.security.permissions import Permission
from app.handlers.admin.organization.audit import format_payload


def test_organization_audit_model_is_registered() -> None:
    assert (
        "organization_audit_events"
        in Base.metadata.tables
    )


def test_organization_audit_table_structure() -> None:
    table = inspect(
        OrganizationAuditEvent
    ).local_table

    assert {
        "id",
        "organization_id",
        "actor_account_id",
        "event_type",
        "source",
        "title",
        "details",
        "payload",
        "created_at",
        "updated_at",
    }.issubset(table.columns.keys())

    assert table.c.organization_id.nullable is False
    assert table.c.actor_account_id.nullable is True


def test_organization_has_audit_relationship() -> None:
    relationships = inspect(
        Organization
    ).relationships

    assert "audit_events" in relationships


def test_organization_permissions_are_mapped() -> None:
    assert permission_codes(
        Permission.ORGANIZATION_VIEW
    ) == frozenset(
        {
            "organization.read",
        }
    )
    assert permission_codes(
        Permission.ORGANIZATION_MANAGE
    ) == frozenset(
        {
            "organization.manage",
        }
    )
    assert permission_codes(
        Permission.ORGANIZATION_AUDIT_VIEW
    ) == frozenset(
        {
            "audit.read.organization",
            "audit.read.platform",
        }
    )


def test_audit_payload_is_readable() -> None:
    assert format_payload(
        {"old_name": "Старая", "new_name": "Новая"}
    ) == [
        "Старое название: Старая",
        "Новое название: Новая",
    ]
