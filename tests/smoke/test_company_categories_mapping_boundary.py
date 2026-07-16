from __future__ import annotations

import ast
from pathlib import Path


HANDLER_PATH = Path(
    "app/handlers/admin/company_categories.py"
)


def test_category_handler_has_no_direct_mapping_dependency() -> None:
    source = HANDLER_PATH.read_text(encoding="utf-8")

    assert "from app.models.legacy_company_mapping import" not in source
    assert "BusinessUnitCardService" in source
    assert "LegacyCompanyMappingService" in source


def test_category_handler_delegates_legacy_conversion() -> None:
    source = HANDLER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef)
    }

    unit_helper = functions[
        "_unit_id_by_legacy_company_id"
    ]
    company_helper = functions[
        "_legacy_company_id_by_unit_id"
    ]

    unit_calls = {
        node.func.attr
        for node in ast.walk(unit_helper)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
    }

    company_calls = {
        node.func.attr
        for node in ast.walk(company_helper)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
    }

    assert "get_unit_id_by_legacy_company_id" in unit_calls
    assert "get_legacy_company_id" in company_calls


def test_category_handler_keeps_callback_compatibility() -> None:
    source = HANDLER_PATH.read_text(encoding="utf-8")

    assert 'F.data.startswith("company:categories:")' in source
    assert "_unit_id_by_legacy_company_id" in source
    assert "_legacy_company_id_by_unit_id" in source
