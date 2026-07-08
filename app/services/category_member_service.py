from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account import Account
from app.models.category import Category
from app.models.category_member import CategoryMember
from app.models.enums import UserRole


class CategoryMemberService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_members(
        self,
        *,
        category_id: int,
        role: UserRole,
    ) -> list[CategoryMember]:
        return list(
            await self.session.scalars(
                select(CategoryMember)
                .options(selectinload(CategoryMember.account))
                .where(
                    CategoryMember.category_id == category_id,
                    CategoryMember.role == role,
                )
                .order_by(CategoryMember.id)
            )
        )

    async def list_available_company_accounts(
        self,
        *,
        company_id: int,
        role: UserRole,
    ) -> list[Account]:
        return list(
            await self.session.scalars(
                select(Account)
                .where(
                    Account.company_id == company_id,
                    Account.role == role,
                    Account.is_active.is_(True),
                    Account.registered.is_(True),
                )
                .order_by(Account.full_name)
            )
        )

    async def add_member(
        self,
        *,
        category_id: int,
        account_id: int,
        role: UserRole,
    ) -> CategoryMember:
        category = await self.session.scalar(
            select(Category).where(Category.id == category_id)
        )

        if category is None:
            raise ValueError("Категория не найдена.")

        account = await self.session.scalar(
            select(Account).where(
                Account.id == account_id,
                Account.company_id == category.company_id,
                Account.role == role,
                Account.is_active.is_(True),
                Account.registered.is_(True),
            )
        )

        if account is None:
            raise ValueError("Аккаунт не найден или не подходит для этой категории.")

        existing = await self.session.scalar(
            select(CategoryMember).where(
                CategoryMember.category_id == category_id,
                CategoryMember.account_id == account_id,
                CategoryMember.role == role,
            )
        )

        if existing is not None:
            return existing

        member = CategoryMember(
            category_id=category_id,
            account_id=account_id,
            role=role,
        )

        self.session.add(member)
        await self.session.commit()
        await self.session.refresh(member)

        return member

    async def remove_member(self, member_id: int) -> CategoryMember:
        member = await self.session.scalar(
            select(CategoryMember)
            .options(selectinload(CategoryMember.account))
            .where(CategoryMember.id == member_id)
        )

        if member is None:
            raise ValueError("Участник категории не найден.")

        await self.session.delete(member)
        await self.session.commit()

        return member
