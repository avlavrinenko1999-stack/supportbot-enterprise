from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account_organizational_unit_membership import (
    AccountOrganizationalUnitMembership,
)
from app.models.company import Company
from app.models.legacy_company_mapping import (
    LegacyCompanyMapping,
)
from app.services.base_service import BaseService


class LegacyCompanyMappingService(BaseService):
    """Изолирует чтение переходного company mapping."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_unit_id_by_legacy_company_id(
        self,
        company_id: int,
    ) -> int | None:
        if company_id <= 0:
            return None

        return await self.session.scalar(
            select(
                LegacyCompanyMapping
                .organizational_unit_id
            ).where(
                LegacyCompanyMapping.company_id
                == company_id
            )
        )

    async def get_legacy_company_id(
        self,
        unit_id: int,
    ) -> int | None:
        if unit_id <= 0:
            return None

        return await self.session.scalar(
            select(
                LegacyCompanyMapping.company_id
            ).where(
                LegacyCompanyMapping
                .organizational_unit_id
                == unit_id
            )
        )

    async def get_primary_membership_company_id(
        self,
        account_id: int,
    ) -> int | None:
        if account_id <= 0:
            return None

        return await self.session.scalar(
            select(
                LegacyCompanyMapping.company_id
            )
            .join(
                AccountOrganizationalUnitMembership,
                AccountOrganizationalUnitMembership
                .organizational_unit_id
                == LegacyCompanyMapping
                .organizational_unit_id,
            )
            .where(
                AccountOrganizationalUnitMembership
                .account_id
                == account_id,
                AccountOrganizationalUnitMembership
                .is_primary
                .is_(True),
                AccountOrganizationalUnitMembership
                .is_active
                .is_(True),
            )
        )

    async def get_legacy_phone(
        self,
        company_id: int,
    ) -> str | None:
        if company_id <= 0:
            return None

        return await self.session.scalar(
            select(Company.phone).where(
                Company.id == company_id
            )
        )

    async def get_phone_by_unit_id(
        self,
        unit_id: int,
    ) -> str | None:
        company_id = await self.get_legacy_company_id(
            unit_id
        )

        if company_id is None:
            return None

        return await self.get_legacy_phone(
            company_id
        )

    async def resolve_assignment_seed_unit_ids(
        self,
        *,
        company_ids: set[int],
        holding_ids: set[int],
        organization_ids: set[int],
    ) -> set[int]:
        conditions = []

        if company_ids:
            conditions.append(
                LegacyCompanyMapping.company_id.in_(
                    company_ids
                )
            )

        if holding_ids:
            conditions.append(
                Company.holding_id.in_(holding_ids)
            )

        if organization_ids:
            conditions.append(
                Company.organization_id.in_(
                    organization_ids
                )
            )

        if not conditions:
            return set()

        return set(
            await self.session.scalars(
                select(
                    LegacyCompanyMapping
                    .organizational_unit_id
                )
                .join(
                    Company,
                    Company.id
                    == LegacyCompanyMapping.company_id,
                )
                .where(or_(*conditions))
            )
        )
