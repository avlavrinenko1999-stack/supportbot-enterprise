from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.holding_audit_event import HoldingAuditEvent
from app.services.base_service import BaseService


class HoldingAuditService(BaseService):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_event(
        self,
        *,
        holding_id: int,
        event_type: str,
        title: str,
        source: str = "system",
        actor_account_id: int | None = None,
        details: str | None = None,
        payload: dict | None = None,
        commit: bool = True,
    ) -> HoldingAuditEvent:
        event = HoldingAuditEvent(
            holding_id=holding_id,
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

    async def list_holding_events(
        self,
        holding_id: int,
        *,
        limit: int = 20,
    ) -> list[HoldingAuditEvent]:
        if limit <= 0:
            return []

        safe_limit = min(limit, 100)

        return list(
            await self.session.scalars(
                select(HoldingAuditEvent)
                .where(
                    HoldingAuditEvent.holding_id == holding_id
                )
                .order_by(
                    HoldingAuditEvent.created_at.desc(),
                    HoldingAuditEvent.id.desc(),
                )
                .limit(safe_limit)
            )
        )
