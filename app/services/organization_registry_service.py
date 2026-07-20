from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.dadata import DadataClient, DadataCompany
from app.models.organization import Organization
from app.services.organization_audit_service import OrganizationAuditService
from app.services.legal_entity_registry_service import audit_json_value


ORGANIZATION_LEGAL_FIELDS = (
    "name",
    "legal_name",
    "inn",
    "kpp",
    "ogrn",
    "legal_address",
    "legal_status",
    "legal_status_code",
    "registration_date",
    "liquidation_date",
    "last_registry_sync_at",
)


class OrganizationRegistryService:
    """Синхронизирует юридические реквизиты организации с DaData."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        client: DadataClient | None = None,
    ):
        self.session = session
        self.client = client or DadataClient()
        self.audit = OrganizationAuditService(session)

    async def sync_organization(
        self,
        organization_id: int,
        *,
        inn: str | None = None,
        actor_account_id: int | None = None,
        source: str = "dadata",
    ) -> Organization:
        organization = await self.session.get(
            Organization,
            organization_id,
        )
        if organization is None:
            raise ValueError("Организация не найдена.")

        clean_inn = self.normalize_inn(inn or organization.inn)
        duplicate = await self.session.scalar(
            select(Organization.id).where(
                Organization.inn == clean_inn,
                Organization.id != organization.id,
            )
        )
        if duplicate is not None:
            raise ValueError("Организация с таким ИНН уже существует.")

        data = await self.client.find_company_by_inn(clean_inn)
        before = organization_legal_snapshot(organization)
        synchronized_at = datetime.now(timezone.utc)

        try:
            self.apply_legal_data(
                organization,
                data,
                synchronized_at=synchronized_at,
            )
            after = organization_legal_snapshot(organization)
            changes = {
                key: {
                    "old": audit_json_value(value),
                    "new": audit_json_value(after[key]),
                }
                for key, value in before.items()
                if value != after[key]
            }
            await self.audit.create_event(
                organization_id=organization.id,
                actor_account_id=actor_account_id,
                event_type="organization_registry_sync",
                source=source,
                title="Юридические данные обновлены из DaData",
                details=f"ИНН: {organization.inn}.",
                payload={"changes": changes},
                commit=False,
            )
            await self.session.commit()
            await self.session.refresh(organization)
        except Exception:
            await self.session.rollback()
            raise

        return organization

    async def list_sync_candidate_ids(
        self,
        *,
        limit: int = 1000,
    ) -> list[int]:
        if limit <= 0:
            return []

        return list(
            await self.session.scalars(
                select(Organization.id)
                .where(
                    Organization.inn.is_not(None),
                    Organization.is_active.is_(True),
                )
                .order_by(
                    Organization.last_registry_sync_at.asc().nullsfirst(),
                    Organization.id,
                )
                .limit(min(limit, 1000))
            )
        )

    @staticmethod
    def normalize_inn(inn: str | None) -> str:
        clean_inn = "".join(
            character
            for character in (inn or "")
            if character.isdigit()
        )
        if len(clean_inn) not in {10, 12}:
            raise ValueError("ИНН должен содержать 10 или 12 цифр.")
        return clean_inn

    @staticmethod
    def apply_legal_data(
        organization: Organization,
        data: DadataCompany,
        *,
        synchronized_at: datetime,
    ) -> None:
        organization.name = data.name
        organization.legal_name = data.legal_name
        organization.inn = data.inn
        organization.kpp = data.kpp
        organization.ogrn = data.ogrn
        organization.legal_address = data.legal_address
        organization.legal_status = data.legal_status
        organization.legal_status_code = data.legal_status_code
        organization.registration_date = data.registration_date
        organization.liquidation_date = data.liquidation_date
        organization.last_registry_sync_at = synchronized_at


def organization_legal_snapshot(organization: Organization) -> dict:
    return {
        field: getattr(organization, field)
        for field in ORGANIZATION_LEGAL_FIELDS
    }
