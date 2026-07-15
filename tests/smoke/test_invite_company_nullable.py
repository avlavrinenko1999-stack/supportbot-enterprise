import asyncio
from pathlib import Path

from sqlalchemy import text

from app.database.db import AsyncSessionLocal
from app.models.invite import Invite


MIGRATION_PATH = Path(
    "migrations/versions/"
    "20260715_01_drop_invite_company_id.py"
)


def test_invite_orm_has_no_company_column() -> None:
    assert "company_id" not in Invite.__table__.columns


def test_invite_company_column_is_absent_in_database() -> None:
    async def verify() -> None:
        async with AsyncSessionLocal() as session:
            column_count = await session.scalar(
                text(
                    """
                    SELECT COUNT(*)
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = 'invites'
                      AND column_name = 'company_id'
                    """
                )
            )

            constraint_count = await session.scalar(
                text(
                    """
                    SELECT COUNT(*)
                    FROM pg_constraint con
                    JOIN pg_class rel
                      ON rel.oid = con.conrelid
                    JOIN pg_namespace nsp
                      ON nsp.oid = rel.relnamespace
                    WHERE nsp.nspname = current_schema()
                      AND rel.relname = 'invites'
                      AND con.conname
                          = 'invites_company_id_fkey'
                    """
                )
            )

            assert column_count == 0
            assert constraint_count == 0

    asyncio.run(verify())


def test_drop_invite_company_migration_contract() -> None:
    source = MIGRATION_PATH.read_text(
        encoding="utf-8"
    )

    assert 'revision: str = "20260715_01"' in source
    assert (
        'down_revision: str | None = "20260714_04"'
        in source
    )

    upgrade_start = source.index("def upgrade()")
    downgrade_start = source.index("def downgrade()")

    upgrade = source[
        upgrade_start:downgrade_start
    ]
    downgrade = source[downgrade_start:]

    assert (
        upgrade.index("op.drop_constraint(")
        < upgrade.index("op.drop_column(")
    )
    assert '"invites_company_id_fkey"' in upgrade
    assert '"company_id"' in upgrade
    assert 'type_="foreignkey"' in upgrade

    assert (
        downgrade.index("op.add_column(")
        < downgrade.index("op.create_foreign_key(")
    )
    assert "sa.Integer()" in downgrade
    assert "nullable=True" in downgrade
    assert '"companies"' in downgrade
    assert '["company_id"]' in downgrade
    assert '["id"]' in downgrade
