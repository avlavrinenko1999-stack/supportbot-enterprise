from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.company import Company
from app.models.enums import InviteRole, UserRole
from app.models.invite import Invite
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

    async def list_company_coordinators(self, company_id: int) -> list[Account]:
        return list(
            await self.session.scalars(
                select(Account)
                .where(
                    Account.company_id == company_id,
                    Account.role == UserRole.COORDINATOR,
                )
                .order_by(Account.id)
            )
        )


    async def get_coordinator(self, coordinator_id: int) -> Account | None:
        return await self.session.scalar(
            select(Account).where(
                Account.id == coordinator_id,
                Account.role == UserRole.COORDINATOR,
            )
        )

    async def set_coordinator_active(
        self,
        coordinator_id: int,
        is_active: bool,
    ) -> Account:
        coordinator = await self.get_coordinator(coordinator_id)

        if coordinator is None:
            raise ValueError("Координатор не найден.")

        coordinator.is_active = is_active

        await self.session.commit()
        await self.session.refresh(coordinator)

        return coordinator


    async def get_pending_company_coordinator_invite(
        self,
        *,
        company_id: int,
        full_name: str,
    ) -> Invite | None:
        return await self.session.scalar(
            select(Invite)
            .where(
                Invite.company_id == company_id,
                Invite.role == InviteRole.COORDINATOR,
                Invite.full_name == full_name,
                Invite.used_at.is_(None),
                Invite.is_active.is_(True),
            )
            .order_by(Invite.id.desc())
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
