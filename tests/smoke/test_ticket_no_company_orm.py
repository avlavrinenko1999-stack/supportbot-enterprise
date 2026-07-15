from __future__ import annotations

import ast
from pathlib import Path

from sqlalchemy import inspect

from app.models.company import Company
from app.models.ticket import Ticket


def test_ticket_has_only_canonical_scope_in_orm() -> None:
    column_names = {
        column.key
        for column in inspect(Ticket).columns
    }
    relationship_names = {
        relationship.key
        for relationship in inspect(Ticket).relationships
    }

    assert "company_id" not in column_names
    assert "business_unit_id" in column_names

    assert "company" not in relationship_names
    assert "business_unit" in relationship_names


def test_company_has_no_ticket_relationship() -> None:
    relationship_names = {
        relationship.key
        for relationship in inspect(Company).relationships
    }

    assert "tickets" not in relationship_names


def test_application_has_no_executable_ticket_company_orm_access() -> None:
    violations: list[str] = []

    for path in sorted(Path("app").rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        lines = source.splitlines()

        for node in ast.walk(tree):
            if not isinstance(node, ast.Attribute):
                continue

            if (
                node.attr in {"company_id", "company"}
                and isinstance(node.value, ast.Name)
                and node.value.id in {"Ticket", "ticket"}
            ):
                violations.append(
                    f"{path}:{node.lineno}:"
                    f"{lines[node.lineno - 1].strip()}"
                )

            if (
                node.attr == "tickets"
                and isinstance(node.value, ast.Name)
                and node.value.id in {"Company", "company"}
            ):
                violations.append(
                    f"{path}:{node.lineno}:"
                    f"{lines[node.lineno - 1].strip()}"
                )

    assert violations == []
