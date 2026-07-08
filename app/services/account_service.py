from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account


class AccountService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_registered_by_telegram_id(
        self,
        telegram_id: int,
    ) -> Account | None:
        return await self.session.scalar(
            select(Account).where(
                Account.telegram_id == telegram_id,
                Account.is_active.is_(True),
                Account.registered.is_(True),
            )
        )
