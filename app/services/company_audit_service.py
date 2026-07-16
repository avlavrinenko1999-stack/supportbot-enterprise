from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company_audit_event import CompanyAuditEvent
from app.services.base_service import BaseService
from app.services.legacy_company_mapping_service import (
    LegacyCompanyMappingService,
)


class CompanyAuditService(BaseService):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapping = LegacyCompanyMappingService(
            session
        )

    async def create_event(
        self,
        *,
        company_id: int,
        event_type: str,
        title: str,
        source: str = "system",
        actor_account_id: int | None = None,
        details: str | None = None,
        payload: dict | None = None,
        commit: bool = True,
    ) -> CompanyAuditEvent:
        event = CompanyAuditEvent(
            company_id=company_id,
            actor_account_id=actor_account_id,
            event_type=event_type,
            source=source,
            title=title,
            details=details,
            payload=payload,
        )

        self.session.add(event)

        if commit:
            await self.session.commit()
            await self.session.refresh(event)
        else:
            await self.session.flush()

        return event

    async def list_company_events(
        self,
        company_id: int,
        *,
        limit: int = 20,
    ) -> list[CompanyAuditEvent]:
        return list(
            await self.session.scalars(
                select(CompanyAuditEvent)
                .where(CompanyAuditEvent.company_id == company_id)
                .order_by(CompanyAuditEvent.created_at.desc())
                .limit(limit)
            )
        )

    async def list_business_unit_events(
        self,
        business_unit_id: int,
        *,
        limit: int = 20,
    ) -> list[CompanyAuditEvent]:
        company_id = (
            await self.mapping.get_legacy_company_id(
                business_unit_id
            )
        )

        if company_id is None:
            return []

        return await self.list_company_events(
            company_id,
            limit=limit,
        )


def company_legal_snapshot(company) -> dict:
    return {
        "name": company.name,
        "inn": company.inn,
        "kpp": company.kpp,
        "ogrn": company.ogrn,
        "legal_name": company.legal_name,
        "legal_address": company.legal_address,
        "legal_status": company.legal_status,
        "legal_status_code": company.legal_status_code,
        "registration_date": company.registration_date,
        "liquidation_date": company.liquidation_date,
        "phone": company.phone,
    }


def diff_snapshots(before: dict, after: dict) -> dict:
    diff = {}

    for key, old_value in before.items():
        new_value = after.get(key)
        if old_value != new_value:
            diff[key] = {
                "old": old_value,
                "new": new_value,
            }

    return diff
