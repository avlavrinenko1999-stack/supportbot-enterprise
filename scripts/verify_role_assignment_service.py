import asyncio
from uuid import uuid4

from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.models.account import Account
from app.models.company import Company
from app.models.enums import UserRole
from app.models.role import Role
from app.security.access_scope import AccessScope
from app.security.company_access import CompanyAccessService
from app.services.role_assignment_service import (
    RoleAssignmentService,
)


async def main() -> None:
    async with AsyncSessionLocal() as session:
        transaction = await session.begin()

        try:
            suffix = uuid4().hex[:10]

            company_a = Company(
                name=f"Scope Test A {suffix}",
                is_active=True,
            )
            company_b = Company(
                name=f"Scope Test B {suffix}",
                is_active=True,
            )

            session.add_all([company_a, company_b])
            await session.flush()

            account = Account(
                telegram_id=None,
                full_name=f"Scope Test User {suffix}",
                role=UserRole.USER,
                company_id=None,
                is_active=True,
                registered=True,
                language="ru",
            )
            session.add(account)
            await session.flush()

            company_admin_role = await session.scalar(
                select(Role).where(
                    Role.code == "company_admin"
                )
            )

            if company_admin_role is None:
                raise RuntimeError(
                    "Системная роль company_admin отсутствует."
                )

            assignment_service = RoleAssignmentService(
                session
            )

            first = await assignment_service.assign_role(
                account_id=account.id,
                role_code="company_admin",
                scope=AccessScope.company(company_a.id),
                grant_reason="Проверка изоляции scope",
                commit=False,
            )

            second = await assignment_service.assign_role(
                account_id=account.id,
                role_code="company_admin",
                scope=AccessScope.company(company_a.id),
                grant_reason="Повторное назначение",
                commit=False,
            )

            if first.id != second.id:
                raise RuntimeError(
                    "Создан дубликат активного назначения."
                )

            access_service = CompanyAccessService(session)

            visible = await access_service.list_visible_companies(
                account
            )
            visible_ids = {company.id for company in visible}

            print("Видимые компании:", sorted(visible_ids))
            print("Разрешённая компания:", company_a.id)
            print("Запрещённая компания:", company_b.id)

            if company_a.id not in visible_ids:
                raise RuntimeError(
                    "Назначенная компания не видна."
                )

            if company_b.id in visible_ids:
                raise RuntimeError(
                    "Обнаружена утечка доступа к чужой компании."
                )

            await assignment_service.revoke_assignment(
                first.id,
                commit=False,
            )

            visible_after_revoke = (
                await access_service.list_visible_companies(
                    account
                )
            )

            if any(
                company.id == company_a.id
                for company in visible_after_revoke
            ):
                raise RuntimeError(
                    "После отзыва роли компания осталась доступна."
                )

            print("Выдача роли: OK")
            print("Защита от дубликатов: OK")
            print("Изоляция компании: OK")
            print("Отзыв роли: OK")
        finally:
            await transaction.rollback()

    print("Тестовые данные отменены транзакцией.")


if __name__ == "__main__":
    asyncio.run(main())
