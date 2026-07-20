from pathlib import Path


HANDLER_PATH = Path(
    "app/handlers/admin/company/edit.py"
)
SERVICE_PATH = Path(
    "app/services/business_unit_creation_service.py"
)


def creation_handler_block() -> str:
    source = HANDLER_PATH.read_text(
        encoding="utf-8"
    )

    start = source.index(
        "async def company_create_finish("
    )
    end = source.index(
        "@router.message("
        "MenuActionFilter("
        "MenuAction.COMPANY_FILL_BY_INN"
        "))",
        start,
    )

    return source[start:end]


def test_creation_handler_uses_canonical_service() -> None:
    block = creation_handler_block()

    assert "BusinessUnitCreationService" in block
    assert "create_from_legal_data" in block
    assert "render_business_unit_card" in block

    assert "CompanyCreationService" not in block
    assert "CompanyAuditService" not in block
    assert "render_company_card" not in block
    assert "company_id" not in block


def test_creation_service_has_no_legacy_company() -> None:
    source = SERVICE_PATH.read_text(
        encoding="utf-8"
    )

    assert "LegalEntity(" in source
    assert "OrganizationalUnit(" in source
    assert "LegalEntityAuditService" in source
    assert "tenant_id" in source

    assert "from app.models.company import" not in source
    assert "Company(" not in source
    assert "LegacyCompanyMapping" not in source
    assert "company_id" not in source


def test_creation_is_atomic_and_tenant_scoped() -> None:
    source = SERVICE_PATH.read_text(
        encoding="utf-8"
    )

    assert "await self.session.flush()" in source
    assert "await self.session.commit()" in source
    assert "await self.session.rollback()" in source
    assert "LegalEntity.tenant_id == tenant_id" in source
    assert "Tenant.is_active.is_(True)" in source
