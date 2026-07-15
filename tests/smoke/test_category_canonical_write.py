from __future__ import annotations

import ast
from pathlib import Path


SERVICE_PATH = Path("app/services/category_service.py")


def _method_node(
    tree: ast.Module,
    method_name: str,
) -> ast.AsyncFunctionDef:
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.AsyncFunctionDef)
            and node.name == method_name
        ):
            return node

    raise AssertionError(f"Method {method_name!r} was not found")


def test_canonical_category_writer_has_no_legacy_company_argument() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    method = _method_node(tree, "create_for_business_unit")

    argument_names = {
        argument.arg
        for argument in (
            list(method.args.posonlyargs)
            + list(method.args.args)
            + list(method.args.kwonlyargs)
        )
    }

    assert "business_unit_id" in argument_names
    assert "legacy_company_id" not in argument_names
    assert "company_id" not in argument_names


def test_canonical_category_writer_does_not_write_company_id() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    method = _method_node(tree, "create_for_business_unit")
    category_calls = [
        node
        for node in ast.walk(method)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Category"
    ]

    assert len(category_calls) == 1

    keyword_names = {
        keyword.arg
        for keyword in category_calls[0].keywords
        if keyword.arg is not None
    }

    assert "business_unit_id" in keyword_names
    assert "company_id" not in keyword_names


def test_legacy_create_adapter_only_resolves_canonical_scope() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    method = _method_node(tree, "create_category")
    calls = [
        node
        for node in ast.walk(method)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "create_for_business_unit"
    ]

    assert len(calls) == 1

    keyword_names = {
        keyword.arg
        for keyword in calls[0].keywords
        if keyword.arg is not None
    }

    assert "business_unit_id" in keyword_names
    assert "legacy_company_id" not in keyword_names
    assert "company_id" not in keyword_names
