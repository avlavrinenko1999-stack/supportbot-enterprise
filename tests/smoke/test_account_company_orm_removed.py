from sqlalchemy import inspect

from app.models.account import Account
from app.models.company import Company


def test_account_has_no_company_column() -> None:
    mapper = inspect(Account)

    assert "company_id" not in {
        column.key
        for column in mapper.columns
    }


def test_account_has_no_company_relationship() -> None:
    mapper = inspect(Account)

    assert "company" not in {
        relationship.key
        for relationship in mapper.relationships
    }


def test_company_has_no_accounts_relationship() -> None:
    mapper = inspect(Company)

    assert "accounts" not in {
        relationship.key
        for relationship in mapper.relationships
    }


def test_account_membership_relationship_remains() -> None:
    mapper = inspect(Account)

    assert (
        "organizational_unit_memberships"
        in {
            relationship.key
            for relationship in mapper.relationships
        }
    )
