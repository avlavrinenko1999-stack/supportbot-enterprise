from __future__ import annotations

import ast
from pathlib import Path


CORE_PATH = Path(
    "app/services/business_unit_service.py"
)
CARD_PATH = Path(
    "app/services/business_unit_card_service.py"
)


def test_business_unit_service_has_no_legacy_dependency() -> None:
    source = CORE_PATH.read_text(encoding="utf-8")

    assert "from app.models.legacy_company_mapping import" not in source
    assert "legacy_company_mapping" not in source
    assert "legacy_company_id" not in source


def test_business_unit_summary_is_canonical() -> None:
    source = CORE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    summary_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "BusinessUnitSummary"
    )

    fields = {
        node.target.id
        for node in summary_class.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
    }

    assert "legacy_company_id" not in fields
    assert {
        "unit",
        "legal_entity",
        "coordinators_count",
        "employees_count",
        "tickets_count",
    } <= fields


def test_card_uses_isolated_legacy_mapping_service() -> None:
    source = CARD_PATH.read_text(encoding="utf-8")

    assert "LegacyCompanyMappingService" in source
    assert (
        "from app.models.legacy_company_mapping import"
        not in source
    )
    assert "self.mapping.get_legacy_company_id" in source
    assert "self.mapping.get_legacy_phone" in source
    assert "legacy_company_id=" not in source
    assert "Company.phone" not in source
    assert "summary.legacy_company_id" not in source
