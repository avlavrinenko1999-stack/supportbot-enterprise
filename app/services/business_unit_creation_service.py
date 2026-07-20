import re
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.dadata import DadataCompany
from app.models.enums import OrganizationalUnitType
from app.models.legal_entity import LegalEntity
from app.models.organizational_unit import (
    OrganizationalUnit,
)
from app.models.tenant import Tenant
from app.services.base_service import BaseService
from app.services.legal_entity_audit_service import (
    LegalEntityAuditService,
)
from app.services.legal_entity_registry_service import (
    LegalEntityRegistryService,
    audit_json_value,
    legal_entity_snapshot,
)


@dataclass(frozen=True)
class BusinessUnitCreationResult:
    """
    Результат канонического создания подразделения.
    """

    unit: OrganizationalUnit
    legal_entity: LegalEntity
    created: bool


class BusinessUnitCreationService(BaseService):
    """
    Создаёт юридическое лицо и корневое рабочее
    подразделение в канонической модели.
    """

    def __init__(
        self,
        session: AsyncSession,
    ):
        self.session = session
        self.audit = LegalEntityAuditService(session)

    @staticmethod
    def normalize_name(
        name: str | None,
    ) -> str:
        value = (name or "").lower()
        value = (
            value.replace("«", "")
            .replace("»", "")
            .replace('"', "")
            .replace("'", "")
        )
        value = re.sub(
            r"\b(ооо|ао|пао|зао|оао|ип|нко|ано)\b",
            " ",
            value,
        )
        value = re.sub(
            r"[^а-яa-z0-9]+",
            " ",
            value,
        )
        return re.sub(
            r"\s+",
            " ",
            value,
        ).strip()

    async def create_from_legal_data(
        self,
        data: DadataCompany,
        *,
        actor_account_id: int | None = None,
    ) -> BusinessUnitCreationResult:
        tenant = await self._require_creation_tenant()

        duplicate = await self._find_duplicate(
            tenant.id,
            data,
        )

        if duplicate is not None:
            unit = await self._get_or_create_root_unit(
                duplicate,
                actor_account_id=actor_account_id,
            )

            return BusinessUnitCreationResult(
                unit=unit,
                legal_entity=duplicate,
                created=False,
            )

        synchronized_at = datetime.now(timezone.utc)

        legal_entity = LegalEntity(
            tenant_id=tenant.id,
            name=data.name,
            is_active=True,
        )

        LegalEntityRegistryService.apply_legal_data(
            legal_entity,
            data,
            synchronized_at=synchronized_at,
        )

        unit = OrganizationalUnit(
            tenant_id=tenant.id,
            legal_entity=legal_entity,
            parent_id=None,
            name=data.name,
            unit_type=(
                OrganizationalUnitType.BUSINESS_UNIT
            ),
            is_active=True,
        )

        try:
            self.session.add(legal_entity)
            self.session.add(unit)
            await self.session.flush()

            await self.audit.create_event(
                legal_entity_id=legal_entity.id,
                actor_account_id=actor_account_id,
                event_type="legal_entity_created",
                source="admin",
                title=(
                    "Созданы юридическое лицо "
                    "и рабочее подразделение"
                ),
                details=(
                    f"Юридическое лицо создано "
                    f"по ИНН {legal_entity.inn}."
                ),
                payload={
                    "legal_entity": audit_json_value(
                        legal_entity_snapshot(
                            legal_entity
                        )
                    ),
                    "business_unit": {
                        "id": unit.id,
                        "name": unit.name,
                        "unit_type": (
                            unit.unit_type.value
                        ),
                    },
                },
                commit=False,
            )

            await self.session.commit()
            await self.session.refresh(legal_entity)
            await self.session.refresh(unit)
        except Exception:
            await self.session.rollback()
            raise

        return BusinessUnitCreationResult(
            unit=unit,
            legal_entity=legal_entity,
            created=True,
        )

    async def _require_creation_tenant(
        self,
    ) -> Tenant:
        tenants = list(
            await self.session.scalars(
                select(Tenant)
                .where(Tenant.is_active.is_(True))
                .order_by(Tenant.id)
                .limit(2)
            )
        )

        if not tenants:
            raise ValueError(
                "Активный контур данных не найден."
            )

        if len(tenants) > 1:
            raise ValueError(
                "Невозможно определить контур данных. "
                "Выберите организационный контур "
                "перед созданием подразделения."
            )

        return tenants[0]

    async def _find_duplicate(
        self,
        tenant_id: int,
        data: DadataCompany,
    ) -> LegalEntity | None:
        if data.inn:
            duplicate = await self.session.scalar(
                select(LegalEntity).where(
                    LegalEntity.tenant_id == tenant_id,
                    LegalEntity.inn == data.inn,
                )
            )

            if duplicate is not None:
                return duplicate

        if data.ogrn:
            duplicate = await self.session.scalar(
                select(LegalEntity).where(
                    LegalEntity.tenant_id == tenant_id,
                    LegalEntity.ogrn == data.ogrn,
                )
            )

            if duplicate is not None:
                return duplicate

        target_names = {
            self.normalize_name(data.name),
            self.normalize_name(data.legal_name),
        }
        target_names.discard("")

        if not target_names:
            return None

        legal_entities = list(
            await self.session.scalars(
                select(LegalEntity)
                .where(
                    LegalEntity.tenant_id == tenant_id
                )
                .order_by(LegalEntity.id)
            )
        )

        for legal_entity in legal_entities:
            current_names = {
                self.normalize_name(legal_entity.name),
                self.normalize_name(
                    legal_entity.legal_name
                ),
            }
            current_names.discard("")

            if target_names & current_names:
                return legal_entity

        return None

    async def _get_or_create_root_unit(
        self,
        legal_entity: LegalEntity,
        *,
        actor_account_id: int | None,
    ) -> OrganizationalUnit:
        unit = await self.session.scalar(
            select(OrganizationalUnit)
            .where(
                OrganizationalUnit.tenant_id
                == legal_entity.tenant_id,
                OrganizationalUnit.legal_entity_id
                == legal_entity.id,
                OrganizationalUnit.parent_id.is_(
                    None
                ),
            )
            .order_by(OrganizationalUnit.id)
        )

        if unit is not None:
            return unit

        unit = OrganizationalUnit(
            tenant_id=legal_entity.tenant_id,
            legal_entity_id=legal_entity.id,
            parent_id=None,
            name=legal_entity.name,
            unit_type=(
                OrganizationalUnitType.BUSINESS_UNIT
            ),
            is_active=True,
        )

        try:
            self.session.add(unit)
            await self.session.flush()

            await self.audit.create_event(
                legal_entity_id=legal_entity.id,
                actor_account_id=actor_account_id,
                event_type="business_unit_created",
                source="admin",
                title=(
                    "Создано рабочее подразделение "
                    "для существующего юридического лица"
                ),
                payload={
                    "business_unit": {
                        "id": unit.id,
                        "name": unit.name,
                        "unit_type": (
                            unit.unit_type.value
                        ),
                    },
                },
                commit=False,
            )

            await self.session.commit()
            await self.session.refresh(unit)
        except Exception:
            await self.session.rollback()
            raise

        return unit
