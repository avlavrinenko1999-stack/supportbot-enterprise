import asyncio

from sqlalchemy import text

from app.database.db import AsyncSessionLocal
from app.models.invite import Invite


def test_invite_orm_has_no_company_column() -> None:
    assert "company_id" not in Invite.__table__.columns


def test_invite_company_id_is_nullable_database_column() -> None:
    async def verify() -> None:
        async with AsyncSessionLocal() as session:
            column = (
                await session.execute(
                    text(
                        """
                        SELECT
                            is_nullable,
                            data_type,
                            column_default
                        FROM information_schema.columns
                        WHERE table_schema = current_schema()
                          AND table_name = 'invites'
                          AND column_name = 'company_id'
                        """
                    )
                )
            ).mappings().one_or_none()

            assert column is not None
            assert column["is_nullable"] == "YES"
            assert column["data_type"] == "integer"
            assert column["column_default"] is None

    asyncio.run(verify())
