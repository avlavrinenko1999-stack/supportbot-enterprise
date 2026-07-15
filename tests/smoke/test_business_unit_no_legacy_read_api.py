from __future__ import annotations

import ast
from pathlib import Path


SERVICE_PATH = Path(
    "app/services/business_unit_service.py"
)


def test_business_unit_service_has_no_legacy_read_method() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    service_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "BusinessUnitService"
    )

    methods = {
        node.name
        for node in service_class.body
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        )
    }

    assert "get_legacy_company_id" not in methods


def test_summary_temporarily_preserves_legacy_callback_id() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert "legacy_company_id: int | None" in source
    assert "LegacyCompanyMapping.company_id" in source
    assert ".get_legacy_company_id(" not in source
