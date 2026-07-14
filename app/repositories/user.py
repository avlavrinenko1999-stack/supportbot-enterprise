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
) -> Account:
    account = Account(
        telegram_id=telegram_id,
        full_name=full_name,
        role=role,
        registered=True,
        is_active=True,
    )

    session.add(account)
    await session.flush()

    return account
