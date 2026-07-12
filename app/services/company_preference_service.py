from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account_company_preference import AccountCompanyPreference
from app.models.company import Company


class CompanyPreferenceService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_or_create(
        self,
        *,
        account_id: int,
        company_id: int,
    ) -> AccountCompanyPreference:
        preference = await self.session.scalar(
            select(AccountCompanyPreference).where(
                AccountCompanyPreference.account_id == account_id,
                AccountCompanyPreference.company_id == company_id,
            )
        )

        if preference is not None:
            return preference

        preference = AccountCompanyPreference(
            account_id=account_id,
            company_id=company_id,
            is_favorite=False,
        )
        self.session.add(preference)
        await self.session.flush()
        return preference

    async def touch_company(self, *, account_id: int, company_id: int) -> None:
        preference = await self._get_or_create(
            account_id=account_id,
            company_id=company_id,
        )
        preference.last_opened_at = datetime.now(timezone.utc)
        await self.session.commit()

    async def set_favorite(
        self,
        *,
        account_id: int,
        company_id: int,
        is_favorite: bool,
    ) -> None:
        preference = await self._get_or_create(
            account_id=account_id,
            company_id=company_id,
        )
        preference.is_favorite = is_favorite
        if preference.last_opened_at is None:
            preference.last_opened_at = datetime.now(timezone.utc)
        await self.session.commit()

    async def is_favorite(self, *, account_id: int, company_id: int) -> bool:
        preference = await self.session.scalar(
            select(AccountCompanyPreference).where(
                AccountCompanyPreference.account_id == account_id,
                AccountCompanyPreference.company_id == company_id,
            )
        )
        return bool(preference and preference.is_favorite)

    async def list_recent_companies(
        self,
        *,
        account_id: int,
        allowed_company_ids: set[int] | None = None,
        limit: int = 8,
    ) -> list[Company]:
        statement = (
            select(AccountCompanyPreference)
            .where(
                AccountCompanyPreference.account_id == account_id,
                AccountCompanyPreference.last_opened_at.is_not(None),
            )
            .options(selectinload(AccountCompanyPreference.company))
            .order_by(AccountCompanyPreference.last_opened_at.desc())
            .limit(limit)
        )

        if allowed_company_ids is not None:
            if not allowed_company_ids:
                return []

            statement = statement.where(
                AccountCompanyPreference.company_id.in_(
                    allowed_company_ids
                )
            )

        preferences = (
            await self.session.scalars(statement)
        ).all()

        return [
            preference.company
            for preference in preferences
            if preference.company is not None
        ]

    async def list_favorite_companies(
        self,
        *,
        account_id: int,
        allowed_company_ids: set[int] | None = None,
    ) -> list[Company]:
        statement = (
            select(AccountCompanyPreference)
            .where(
                AccountCompanyPreference.account_id == account_id,
                AccountCompanyPreference.is_favorite.is_(True),
            )
            .options(selectinload(AccountCompanyPreference.company))
            .order_by(
                AccountCompanyPreference.pin_order.asc().nullslast(),
                AccountCompanyPreference.updated_at.desc(),
            )
        )

        if allowed_company_ids is not None:
            if not allowed_company_ids:
                return []

            statement = statement.where(
                AccountCompanyPreference.company_id.in_(
                    allowed_company_ids
                )
            )

        preferences = (
            await self.session.scalars(statement)
        ).all()

        return [
            preference.company
            for preference in preferences
            if preference.company is not None
        ]
