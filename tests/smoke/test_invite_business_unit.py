from pathlib import Path

from app.models.invite import Invite
from app.services.invite_service import (
    InviteService,
)


MODEL_PATH = Path("app/models/invite.py")
SERVICE_PATH = Path("app/services/invite_service.py")
MIGRATION_PATH = Path("migrations/versions/20260714_02_add_invite_business_unit.py")


def test_invite_model_has_business_unit() -> None:
    assert hasattr(
        Invite,
        "organizational_unit_id",
    )
    assert hasattr(
        Invite,
        "business_unit",
    )


def test_invite_company_bridge_remains() -> None:
    assert hasattr(Invite, "company_id")
    assert hasattr(Invite, "company")


def test_invite_service_dual_writes_scope() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert "LegacyCompanyMapping" in source
    assert "business_unit_id" in source
    assert "organizational_unit_id=" in source
    assert "company_id=company.id" in source


def test_migration_backfills_business_unit() -> None:
    source = MIGRATION_PATH.read_text(encoding="utf-8")

    assert "legacy_company_mappings" in source
    assert "organizational_unit_id" in source
    assert "nullable=False" in source
    assert "20260714_01" in source


def test_invite_service_contract_remains() -> None:
    assert hasattr(
        InviteService,
        "create_invite",
    )
    assert hasattr(
        InviteService,
        "register_by_token",
    )


def test_model_relationship_contract() -> None:
    source = MODEL_PATH.read_text(encoding="utf-8")

    assert '"OrganizationalUnit"' in source
    assert 'back_populates="invites"' in source
