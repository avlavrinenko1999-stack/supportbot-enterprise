from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.services.invite_service import InviteService
from app.repositories.invite import get_active_invite_by_hash, mark_invite_used
from app.repositories.user import create_account, get_account_by_telegram_id
from app.utils.security import hash_token


INVITE_ROLE_TO_USER_ROLE = {
    "coordinator": UserRole.COORDINATOR,
    "operator": UserRole.OPERATOR,
    "user": UserRole.USER,
}


async def get_current_account(
    session: AsyncSession,
    telegram_id: int,
):
    return await get_account_by_telegram_id(session, telegram_id)


async def register_by_invite_token(
    session: AsyncSession,
    telegram_id: int,
    token: str,
):
    existing_account = await get_account_by_telegram_id(session, telegram_id)

    if existing_account:
        return existing_account, "already_registered"

    token_hash = hash_token(token)

    invite = await get_active_invite_by_hash(session, token_hash)

    if not invite:
        return None, "invalid_invite"

    role = INVITE_ROLE_TO_USER_ROLE[invite.role.value]

    account = await create_account(
        session=session,
        telegram_id=telegram_id,
        full_name=invite.full_name,
        role=role,
        company_id=invite.company_id,
    )

    await session.flush()

    await InviteService(session).ensure_primary_membership(
        account_id=account.id,
        organizational_unit_id=(invite.organizational_unit_id),
    )

    await mark_invite_used(session, invite)

    await session.commit()

    return account, "registered"
