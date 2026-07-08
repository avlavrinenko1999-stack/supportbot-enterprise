from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invite import Invite
from app.models.user import User


class InviteService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register_by_token(
        self,
        token: str,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
    ) -> User:
        invite = await self.session.scalar(
            select(Invite)
            .where(Invite.token == token)
            .with_for_update()
        )

        if invite is None:
            raise ValueError("Приглашение не найдено")

        if invite.used_at is not None:
            raise ValueError("Приглашение уже использовано")

        if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
            raise ValueError("Срок действия приглашения истёк")

        existing_user = await self.session.scalar(
            select(User).where(User.telegram_id == telegram_id)
        )

        if existing_user:
            return existing_user

        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            company_id=invite.company_id,
            role=invite.role,
            is_active=True,
        )

        invite.used_at = datetime.now(timezone.utc)
        invite.used_by_telegram_id = telegram_id

        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)

        return user
