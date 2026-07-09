from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.enums import UserRole


class EmployeeService:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, account_id: int) -> Account | None:
        return await self.session.scalar(
            select(Account).where(Account.id == account_id)
        )

    async def list_all(self) -> list[Account]:
        return list(
            await self.session.scalars(
                select(Account).order_by(Account.full_name)
            )
        )

    async def list_by_role(
        self,
        role: UserRole,
    ) -> list[Account]:
        return list(
            await self.session.scalars(
                select(Account)
                .where(Account.role == role)
                .order_by(Account.full_name)
            )
        )

    async def list_by_company(
        self,
        company_id: int,
    ) -> list[Account]:
        return list(
            await self.session.scalars(
                select(Account)
                .where(Account.company_id == company_id)
                .order_by(Account.full_name)
            )
        )

    async def activate(self, account: Account):
        account.is_active = True
        await self.session.commit()

    async def deactivate(self, account: Account):
        account.is_active = False
        await self.session.commit()

    async def change_role(
        self,
        account: Account,
        role: UserRole,
    ):
        account.role = role
        await self.session.commit()

    async def move_to_company(
        self,
        account: Account,
        company_id: int,
    ):
        account.company_id = company_id
        await self.session.commit()
