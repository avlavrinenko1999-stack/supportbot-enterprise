from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invite import Invite


async def get_active_invite_by_hash(
    session: AsyncSession,
    token_hash: str,
) -> Invite | None:
    now = datetime.now(timezone.utc)

    result = await session.execute(
        select(Invite).where(
            Invite.token_hash == token_hash,
            Invite.is_active.is_(True),
            Invite.used_at.is_(None),
            Invite.expires_at > now,
        )
    )

    return result.scalar_one_or_none()


async def mark_invite_used(
    session: AsyncSession,
    invite: Invite,
) -> None:
    invite.is_active = False
    invite.used_at = datetime.now(timezone.utc)
    await session.flush()
