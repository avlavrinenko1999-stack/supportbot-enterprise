import ast
from pathlib import Path

from app.services.invite_service import (
    InviteService,
)


INVITE_SERVICE = Path("app/services/invite_service.py")

COORDINATOR_SERVICE = Path("app/services/business_unit_coordinator_service.py")


def test_canonical_invite_api_exists() -> None:
    assert hasattr(
        InviteService,
        "create_for_business_unit",
    )


def test_canonical_api_validates_business_unit() -> None:
    source = INVITE_SERVICE.read_text(encoding="utf-8")

    start = source.index("async def create_for_business_unit(")
    end = source.index(
        "async def register_by_token(",
        start,
    )
    block = source[start:end]

    assert "OrganizationalUnit" in block
    assert "business_unit_id" in block
    assert "is_active" in block


def test_canonical_api_uses_private_record_factory() -> None:
    source = INVITE_SERVICE.read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)

    method = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(
                node,
                ast.AsyncFunctionDef,
            )
            and node.name
            == "create_for_business_unit"
        ),
        None,
    )

    assert method is not None

    block = ast.get_source_segment(
        source,
        method,
    )

    assert block is not None
    assert (
        "self._private_create_invite_record("
        in block
    )
    assert "organizational_unit_id=" in block
    assert "company_id" not in block
    assert "LegacyCompanyMapping" not in block
    assert "legacy_company_id" not in block
    assert "self.create_invite(" not in block


def test_coordinator_service_uses_canonical_api() -> None:
    source = COORDINATOR_SERVICE.read_text(encoding="utf-8")

    assert "InviteService" in source
    assert "create_for_business_unit" in source
    assert "InviteRole.COORDINATOR" in source


def test_coordinator_service_has_no_company_bridge() -> None:
    source = COORDINATOR_SERVICE.read_text(encoding="utf-8")

    assert "LegacyCompanyMapping" not in source
    assert "AccountAdminService" not in source
    assert "get_legacy_company_id" not in source
    assert "legacy_company_id" not in source
    assert "company_id=" not in source


def test_legacy_invite_api_remains_available() -> None:
    assert hasattr(
        InviteService,
        "create_invite",
    )

    source = INVITE_SERVICE.read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)

    method = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(
                node,
                ast.AsyncFunctionDef,
            )
            and node.name == "create_invite"
        ),
        None,
    )

    assert method is not None

    block = ast.get_source_segment(
        source,
        method,
    )

    assert block is not None
    assert "company_id: int" in block
    assert "self.mapping" in block
    assert (
        "get_unit_id_by_legacy_company_id"
        in block
    )
    assert "LegacyCompanyMapping." not in block
    assert "organizational_unit_id" in block
    assert (
        "self._private_create_invite_record("
        in block
    )
    assert "company_id=company.id" not in block
    assert "company_id=" not in block
