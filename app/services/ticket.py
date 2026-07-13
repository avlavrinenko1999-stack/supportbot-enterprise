from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account import Account
from app.models.legacy_company_mapping import (
    LegacyCompanyMapping,
)
from app.models.organizational_unit import (
    OrganizationalUnit,
)
from app.models.ticket import Ticket
from app.services.base_service import BaseService


class TicketService(BaseService):
    """
    Прикладной сервис обращений.

    Основная область принадлежности обращения —
    OrganizationalUnit.

    company_id заполняется только при наличии
    LegacyCompanyMapping и используется временно
    старыми участками приложения.
    """

    MIN_SUBJECT_LENGTH = 3
    MAX_SUBJECT_LENGTH = 255
    DEFAULT_LIMIT = 50
    MAX_LIMIT = 200

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_ticket(
        self,
        ticket_id: int,
    ) -> Ticket | None:
        if ticket_id <= 0:
            return None

        return await self.session.scalar(
            select(Ticket)
            .where(Ticket.id == ticket_id)
            .options(
                selectinload(Ticket.business_unit),
                selectinload(Ticket.author),
                selectinload(Ticket.operator),
                selectinload(Ticket.category),
            )
        )

    async def require_ticket(
        self,
        ticket_id: int,
    ) -> Ticket:
        ticket = await self.get_ticket(ticket_id)

        if ticket is None:
            raise ValueError(
                "Обращение не найдено."
            )

        return ticket

    async def list_for_business_unit(
        self,
        business_unit_id: int,
        *,
        limit: int = DEFAULT_LIMIT,
    ) -> list[Ticket]:
        if business_unit_id <= 0:
            return []

        safe_limit = max(
            1,
            min(limit, self.MAX_LIMIT),
        )

        return list(
            await self.session.scalars(
                select(Ticket)
                .where(
                    Ticket.business_unit_id
                    == business_unit_id
                )
                .options(
                    selectinload(
                        Ticket.business_unit
                    ),
                    selectinload(Ticket.author),
                    selectinload(Ticket.operator),
                    selectinload(Ticket.category),
                )
                .order_by(
                    Ticket.created_at.desc(),
                    Ticket.id.desc(),
                )
                .limit(safe_limit)
            )
        )

    async def count_for_business_unit(
        self,
        business_unit_id: int,
    ) -> int:
        if business_unit_id <= 0:
            return 0

        return (
            await self.session.scalar(
                select(func.count(Ticket.id)).where(
                    Ticket.business_unit_id
                    == business_unit_id
                )
            )
            or 0
        )

    async def create_ticket(
        self,
        *,
        business_unit_id: int,
        account_id: int,
        subject: str,
        operator_id: int | None = None,
        category_id: int | None = None,
    ) -> Ticket:
        clean_subject = self._validate_subject(
            subject
        )

        business_unit = await self.session.get(
            OrganizationalUnit,
            business_unit_id,
        )

        if business_unit is None:
            raise ValueError(
                "Рабочее подразделение не найдено."
            )

        if not business_unit.is_active:
            raise ValueError(
                "Нельзя создать обращение "
                "в отключённом подразделении."
            )

        account = await self.session.get(
            Account,
            account_id,
        )

        if account is None:
            raise ValueError(
                "Автор обращения не найден."
            )

        if not account.is_active:
            raise ValueError(
                "Автор обращения отключён."
            )

        legacy_company_id = (
            await self.session.scalar(
                select(
                    LegacyCompanyMapping.company_id
                ).where(
                    LegacyCompanyMapping
                    .organizational_unit_id
                    == business_unit_id
                )
            )
        )

        ticket = Ticket(
            business_unit_id=business_unit_id,
            company_id=legacy_company_id,
            account_id=account_id,
            operator_id=operator_id,
            category_id=category_id,
            subject=clean_subject,
        )

        self.session.add(ticket)

        try:
            await self.session.commit()
            await self.session.refresh(ticket)
        except Exception:
            await self.session.rollback()
            raise

        return ticket

    @classmethod
    def _validate_subject(
        cls,
        subject: str | None,
    ) -> str:
        clean_subject = " ".join(
            (subject or "").split()
        )

        if (
            len(clean_subject)
            < cls.MIN_SUBJECT_LENGTH
        ):
            raise ValueError(
                "Тема обращения слишком короткая."
            )

        if (
            len(clean_subject)
            > cls.MAX_SUBJECT_LENGTH
        ):
            raise ValueError(
                "Тема обращения слишком длинная."
            )

        return clean_subject
