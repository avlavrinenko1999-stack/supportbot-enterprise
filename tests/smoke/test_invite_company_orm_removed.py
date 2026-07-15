import ast
from pathlib import Path

from sqlalchemy import inspect

from app.models.company import Company
from app.models.invite import Invite


INVITE_SERVICE_PATH = Path(
    "app/services/invite_service.py"
)


def test_invite_has_no_company_column() -> None:
    mapper = inspect(Invite)

    assert "company_id" not in {
        column.key
        for column in mapper.columns
    }


def test_invite_has_no_company_relationship() -> None:
    mapper = inspect(Invite)

    assert "company" not in {
        relationship.key
        for relationship in mapper.relationships
    }


def test_company_has_no_invites_relationship() -> None:
    mapper = inspect(Company)

    assert "invites" not in {
        relationship.key
        for relationship in mapper.relationships
    }


def test_invite_business_unit_relationship_remains() -> None:
    mapper = inspect(Invite)

    assert "organizational_unit_id" in {
        column.key
        for column in mapper.columns
    }

    assert "business_unit" in {
        relationship.key
        for relationship in mapper.relationships
    }


def test_record_factory_has_no_company_argument() -> None:
    source = INVITE_SERVICE_PATH.read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)

    method = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name
        == "_private_create_invite_record"
    )

    argument_names = {
        argument.arg
        for argument in (
            list(method.args.args)
            + list(method.args.kwonlyargs)
        )
    }

    assert "organizational_unit_id" in argument_names
    assert "company_id" not in argument_names

    block = ast.get_source_segment(
        source,
        method,
    )

    assert block is not None
    assert "company_id=" not in block


def test_canonical_api_has_no_legacy_mapping() -> None:
    source = INVITE_SERVICE_PATH.read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)

    method = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name == "create_for_business_unit"
    )

    block = ast.get_source_segment(
        source,
        method,
    )

    assert block is not None
    assert "LegacyCompanyMapping" not in block
    assert "Company" not in block
    assert "company_id" not in block
    assert "_private_create_invite_record" in block
