from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account


class BaseApplication:
    @staticmethod
    async def get_current_account(
        session: AsyncSession,
        telegram_id: int,
    ) -> Account | None:
        return await session.scalar(
            select(Account).where(
                Account.telegram_id == telegram_id,
                Account.is_active.is_(True),
                Account.registered.is_(True),
            )
        )

    @staticmethod
    def profile_not_found_text() -> str:
        return "Профиль не найден."
