from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.company import Company
from app.models.enums import UserRole


class EmployeeService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, account_id: int) -> Account | None:
        return await self.session.scalar(
            select(Account).where(Account.id == account_id)
        )

    async def get_active_registered(self, account_id: int) -> Account | None:
        return await self.session.scalar(
            select(Account).where(
                Account.id == account_id,
                Account.is_active.is_(True),
                Account.registered.is_(True),
            )
        )

    async def list_all(self) -> list[Account]:
        return list(
            await self.session.scalars(
                select(Account).order_by(Account.full_name)
            )
        )

    async def list_by_role(self, role: UserRole) -> list[Account]:
        return list(
            await self.session.scalars(
                select(Account)
                .where(Account.role == role)
                .order_by(Account.full_name)
            )
        )

    async def list_by_company(self, company_id: int) -> list[Account]:
        return list(
            await self.session.scalars(
                select(Account)
                .where(Account.company_id == company_id)
                .order_by(Account.full_name)
            )
        )

    async def list_by_company_and_role(
        self,
        company_id: int,
        role: UserRole,
    ) -> list[Account]:
        return list(
            await self.session.scalars(
                select(Account)
                .where(
                    Account.company_id == company_id,
                    Account.role == role,
                )
                .order_by(Account.full_name)
            )
        )

    async def search(
        self,
        query: str,
        *,
        company_id: int | None = None,
        role: UserRole | None = None,
        limit: int = 20,
    ) -> list[Account]:
        clean_query = query.strip().lower()

        statement = select(Account)

        if clean_query:
            like_query = f"%{clean_query}%"
            statement = statement.where(
                or_(
                    func.lower(Account.full_name).like(like_query),
                    func.cast(Account.telegram_id, str).like(like_query),
                )
            )

        if company_id is not None:
            statement = statement.where(Account.company_id == company_id)

        if role is not None:
            statement = statement.where(Account.role == role)

        statement = statement.order_by(Account.full_name).limit(limit)

        return list(await self.session.scalars(statement))

    async def activate(self, account: Account) -> Account:
        account.is_active = True
        await self.session.commit()
        await self.session.refresh(account)
        return account

    async def deactivate(self, account: Account) -> Account:
        account.is_active = False
        await self.session.commit()
        await self.session.refresh(account)
        return account

    async def change_role(self, account: Account, role: UserRole) -> Account:
        account.role = role
        await self.session.commit()
        await self.session.refresh(account)
        return account

    async def move_to_company(self, account: Account, company_id: int | None) -> Account:
        if company_id is not None:
            company = await self.session.scalar(
                select(Company).where(Company.id == company_id)
            )
            if company is None:
                raise ValueError("Компания не найдена.")

        account.company_id = company_id
        await self.session.commit()
        await self.session.refresh(account)
        return account

    async def count_by_company(self, company_id: int) -> int:
        return int(
            await self.session.scalar(
                select(func.count(Account.id)).where(Account.company_id == company_id)
            )
            or 0
        )

    async def count_by_role(self, role: UserRole) -> int:
        return int(
            await self.session.scalar(
                select(func.count(Account.id)).where(Account.role == role)
            )
            or 0
        )
