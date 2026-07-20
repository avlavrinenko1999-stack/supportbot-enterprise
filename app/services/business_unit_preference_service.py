from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account_business_unit_preference import (
    AccountBusinessUnitPreference,
)
from app.models.organizational_unit import (
    OrganizationalUnit,
)
from app.services.base_service import BaseService


class BusinessUnitPreferenceService(BaseService):
    """
    Избранные и последние рабочие подразделения.

    Сервис работает непосредственно с
    OrganizationalUnit является единственным источником подразделений.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_or_create(
        self,
        *,
        account_id: int,
        business_unit_id: int,
    ) -> AccountBusinessUnitPreference:
        preference = await self.session.scalar(
            select(
                AccountBusinessUnitPreference
            ).where(
                AccountBusinessUnitPreference
                .account_id
                == account_id,
                AccountBusinessUnitPreference
                .business_unit_id
                == business_unit_id,
            )
        )

        if preference is not None:
            return preference

        unit_exists = await self.session.scalar(
            select(OrganizationalUnit.id).where(
                OrganizationalUnit.id
                == business_unit_id
            )
        )

        if unit_exists is None:
            raise ValueError(
                "Рабочее подразделение не найдено."
            )

        preference = (
            AccountBusinessUnitPreference(
                account_id=account_id,
                business_unit_id=business_unit_id,
                is_favorite=False,
            )
        )

        self.session.add(preference)
        await self.session.flush()

        return preference

    async def touch_unit(
        self,
        *,
        account_id: int,
        business_unit_id: int,
    ) -> None:
        preference = await self._get_or_create(
            account_id=account_id,
            business_unit_id=business_unit_id,
        )

        preference.last_opened_at = (
            datetime.now(timezone.utc)
        )

        await self.session.commit()

    async def set_favorite(
        self,
        *,
        account_id: int,
        business_unit_id: int,
        is_favorite: bool,
    ) -> None:
        preference = await self._get_or_create(
            account_id=account_id,
            business_unit_id=business_unit_id,
        )

        preference.is_favorite = is_favorite

        if preference.last_opened_at is None:
            preference.last_opened_at = (
                datetime.now(timezone.utc)
            )

        await self.session.commit()

    async def is_favorite(
        self,
        *,
        account_id: int,
        business_unit_id: int,
    ) -> bool:
        preference = await self.session.scalar(
            select(
                AccountBusinessUnitPreference
                .is_favorite
            ).where(
                AccountBusinessUnitPreference
                .account_id
                == account_id,
                AccountBusinessUnitPreference
                .business_unit_id
                == business_unit_id,
            )
        )

        return bool(preference)

    async def list_recent_units(
        self,
        *,
        account_id: int,
        allowed_unit_ids: set[int] | None = None,
        limit: int = 8,
    ) -> list[OrganizationalUnit]:
        statement = (
            select(
                AccountBusinessUnitPreference
            )
            .where(
                AccountBusinessUnitPreference
                .account_id
                == account_id,
                AccountBusinessUnitPreference
                .last_opened_at
                .is_not(None),
            )
            .options(
                selectinload(
                    AccountBusinessUnitPreference
                    .business_unit
                ).selectinload(
                    OrganizationalUnit
                    .legal_entity
                )
            )
            .order_by(
                AccountBusinessUnitPreference
                .last_opened_at.desc()
            )
            .limit(limit)
        )

        if allowed_unit_ids is not None:
            if not allowed_unit_ids:
                return []

            statement = statement.where(
                AccountBusinessUnitPreference
                .business_unit_id.in_(
                    allowed_unit_ids
                )
            )

        preferences = list(
            await self.session.scalars(statement)
        )

        return [
            preference.business_unit
            for preference in preferences
            if preference.business_unit is not None
        ]

    async def list_favorite_units(
        self,
        *,
        account_id: int,
        allowed_unit_ids: set[int] | None = None,
    ) -> list[OrganizationalUnit]:
        statement = (
            select(
                AccountBusinessUnitPreference
            )
            .where(
                AccountBusinessUnitPreference
                .account_id
                == account_id,
                AccountBusinessUnitPreference
                .is_favorite.is_(True),
            )
            .options(
                selectinload(
                    AccountBusinessUnitPreference
                    .business_unit
                ).selectinload(
                    OrganizationalUnit
                    .legal_entity
                )
            )
            .order_by(
                AccountBusinessUnitPreference
                .pin_order.asc().nullslast(),
                AccountBusinessUnitPreference
                .updated_at.desc(),
            )
        )

        if allowed_unit_ids is not None:
            if not allowed_unit_ids:
                return []

            statement = statement.where(
                AccountBusinessUnitPreference
                .business_unit_id.in_(
                    allowed_unit_ids
                )
            )

        preferences = list(
            await self.session.scalars(statement)
        )

        return [
            preference.business_unit
            for preference in preferences
            if preference.business_unit is not None
        ]
