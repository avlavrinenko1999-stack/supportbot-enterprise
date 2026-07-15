from __future__ import annotations

import ast
from pathlib import Path


SERVICE_PATH = Path("app/services/category_service.py")


def _service_methods() -> set[str]:
    source = SERVICE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    service = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "CategoryService"
    )

    return {
        node.name
        for node in service.body
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        )
    }


def test_category_service_has_only_canonical_create_api() -> None:
    methods = _service_methods()

    assert "create_for_business_unit" in methods
    assert "create_category" not in methods
    assert "_require_business_unit_id" not in methods


def test_category_service_has_no_legacy_mapping_dependency() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert "LegacyCompanyMapping" not in source
    assert "legacy_company_mapping" not in source


def test_repository_has_no_category_create_adapter_calls() -> None:
    calls: list[str] = []

    for root_name in ("app", "tests"):
        for path in sorted(Path(root_name).rglob("*.py")):
            if path == Path(__file__):
                continue

            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))

            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue

                if (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "create_category"
                ):
                    calls.append(
                        f"{path}:{node.lineno}:create_category"
                    )

                if (
                    isinstance(node.func, ast.Name)
                    and node.func.id == "create_category"
                ):
                    calls.append(
                        f"{path}:{node.lineno}:create_category"
                    )

    assert calls == []
