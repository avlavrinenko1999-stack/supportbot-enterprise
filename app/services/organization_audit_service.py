from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization_audit_event import (
    OrganizationAuditEvent,
)
from app.services.base_service import BaseService


class OrganizationAuditService(BaseService):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_event(
        self,
        *,
        organization_id: int,
        event_type: str,
        title: str,
        source: str = "system",
        actor_account_id: int | None = None,
        details: str | None = None,
        payload: dict | None = None,
        commit: bool = True,
    ) -> OrganizationAuditEvent:
        event = OrganizationAuditEvent(
            organization_id=organization_id,
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

    async def list_organization_events(
        self,
        organization_id: int,
        *,
        limit: int = 20,
    ) -> list[OrganizationAuditEvent]:
        if limit <= 0:
            return []

        safe_limit = min(limit, 100)

        return list(
            await self.session.scalars(
                select(OrganizationAuditEvent)
                .where(
                    OrganizationAuditEvent.organization_id
                    == organization_id
                )
                .order_by(
                    OrganizationAuditEvent.created_at.desc(),
                    OrganizationAuditEvent.id.desc(),
                )
                .limit(safe_limit)
            )
        )
