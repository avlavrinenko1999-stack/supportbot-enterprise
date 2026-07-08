from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.company import Company
from app.models.enums import InviteRole, UserRole
from app.services.invite_service import CreatedInvite, InviteService


@dataclass(frozen=True)
class CoordinatorInviteResult:
    company: Company
    created_invite: CreatedInvite


class CoordinatorService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_coordinators(self) -> list[Account]:
        return list(
            await self.session.scalars(
                select(Account)
                .where(Account.role == UserRole.COORDINATOR)
                .order_by(Account.id)
            )
        )

    async def create_coordinator_invite(
        self,
        *,
        admin: Account,
        company_id: int,
        full_name: str,
        bot_username: str,
    ) -> CoordinatorInviteResult:
        company = await self.session.scalar(
            select(Company).where(
                Company.id == company_id,
                Company.is_active.is_(True),
            )
        )

        if company is None:
            raise ValueError("Компания не найдена или отключена.")

        invite_service = InviteService(self.session)

        created_invite = await invite_service.create_invite(
            created_by=admin,
            company_id=company.id,
            role=InviteRole.COORDINATOR,
            full_name=full_name,
            bot_username=bot_username,
        )

        return CoordinatorInviteResult(
            company=company,
            created_invite=created_invite,
        )
