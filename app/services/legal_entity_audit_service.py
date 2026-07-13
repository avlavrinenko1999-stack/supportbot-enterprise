from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.legal_entity_audit_event import (
    LegalEntityAuditEvent,
)
from app.services.base_service import BaseService


class LegalEntityAuditService(BaseService):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_event(
        self,
        *,
        legal_entity_id: int,
        event_type: str,
        title: str,
        source: str = "system",
        actor_account_id: int | None = None,
        details: str | None = None,
        payload: dict | None = None,
        commit: bool = True,
    ) -> LegalEntityAuditEvent:
        event = LegalEntityAuditEvent(
            legal_entity_id=legal_entity_id,
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

    async def list_events(
        self,
        legal_entity_id: int,
        *,
        limit: int = 20,
    ) -> list[LegalEntityAuditEvent]:
        if limit <= 0:
            return []

        return list(
            await self.session.scalars(
                select(LegalEntityAuditEvent)
                .where(
                    LegalEntityAuditEvent.legal_entity_id
                    == legal_entity_id
                )
                .order_by(
                    LegalEntityAuditEvent.created_at.desc(),
                    LegalEntityAuditEvent.id.desc(),
                )
                .limit(min(limit, 100))
            )
        )
