from __future__ import annotations

import ast
from pathlib import Path


SERVICE_PATH = Path("app/services/category_service.py")

REMOVED_METHODS = {
    "list_active_categories",
    "list_archived_categories",
}

CANONICAL_METHODS = {
    "list_active_for_business_unit",
    "list_archived_for_business_unit",
}


def _category_service_methods() -> set[str]:
    source = SERVICE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    category_service = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "CategoryService"
    )

    return {
        node.name
        for node in category_service.body
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        )
    }


def test_category_service_has_no_legacy_read_api() -> None:
    methods = _category_service_methods()

    assert methods.isdisjoint(REMOVED_METHODS)
    assert CANONICAL_METHODS.issubset(methods)


def test_repository_has_no_calls_to_removed_category_read_api() -> None:
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
                    and node.func.attr in REMOVED_METHODS
                ):
                    calls.append(
                        f"{path}:{node.lineno}:{node.func.attr}"
                    )

                if (
                    isinstance(node.func, ast.Name)
                    and node.func.id in REMOVED_METHODS
                ):
                    calls.append(
                        f"{path}:{node.lineno}:{node.func.id}"
                    )

    assert calls == []
