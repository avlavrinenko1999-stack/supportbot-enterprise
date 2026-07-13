from sqlalchemy import inspect

from app.models import (
    Base,
    LegalEntity,
    LegalEntityAuditEvent,
)


def test_legal_entity_audit_table_is_registered() -> None:
    assert (
        "legal_entity_audit_events"
        in Base.metadata.tables
    )


def test_legal_entity_audit_structure() -> None:
    table = inspect(
        LegalEntityAuditEvent
    ).local_table

    assert {
        "id",
        "legal_entity_id",
        "actor_account_id",
        "event_type",
        "source",
        "title",
        "details",
        "payload",
        "created_at",
        "updated_at",
    }.issubset(table.columns.keys())


def test_legal_entity_has_audit_relationship() -> None:
    assert (
        "audit_events"
        in inspect(LegalEntity).relationships
    )
