from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account


async def get_account_by_telegram_id(
    session: AsyncSession,
    telegram_id: int,
) -> Account | None:
    result = await session.execute(
        select(Account).where(Account.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def create_account(
    session: AsyncSession,
    telegram_id: int,
    full_name: str,
    role,
    company_id: int | None,
) -> Account:
    account = Account(
        telegram_id=telegram_id,
        full_name=full_name,
        role=role,
        company_id=company_id,
        registered=True,
        is_active=True,
    )

    session.add(account)
    await session.flush()

    return account
