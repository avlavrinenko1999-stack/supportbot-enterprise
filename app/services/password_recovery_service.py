import hashlib
import hmac
import html
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.account import Account
from app.models.mail_settings import MailSettings
from app.models.password_access_code import PasswordAccessCode
from app.services.web_identity_service import WebIdentityService


class PasswordRecoveryService:
    CODE_TTL = timedelta(hours=1)
    RESET_TOKEN_TTL = timedelta(minutes=15)
    RESEND_DELAY = timedelta(seconds=60)
    MAX_ATTEMPTS = 5

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _hash_code(account_id: int, code: str) -> str:
        payload = f"password-access:{account_id}:{code}".encode()
        return hmac.new(
            settings.SECRET_KEY.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _hash_reset_token(token: str) -> str:
        return hmac.new(
            settings.SECRET_KEY.encode(),
            f"password-reset:{token}".encode(),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _email_html(full_name: str, code: str) -> str:
        safe_name = html.escape(full_name)
        safe_code = html.escape(code)
        return f'''<!doctype html>
<html lang="ru"><body style="margin:0;background:#090b0e;color:#f7f2e8;font-family:Arial,sans-serif">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#090b0e;padding:32px 12px"><tr><td align="center">
<table role="presentation" width="560" cellspacing="0" cellpadding="0" style="max-width:560px;background:#171b21;border:1px solid #65583f;border-radius:22px;overflow:hidden">
<tr><td style="height:6px;background:#c8a86b"></td></tr>
<tr><td style="padding:38px 42px">
<div style="display:inline-block;padding:10px 14px;border:1px solid #65583f;border-radius:12px;color:#e4c78f;font-weight:700">S</div>
<h1 style="margin:26px 0 12px;font-size:26px;line-height:1.25;color:#f7f2e8">Одноразовый код доступа</h1>
<p style="margin:0 0 20px;color:#c8c1b5;font-size:16px;line-height:1.55">Здравствуйте, {safe_name}! Используйте этот код для входа в SupportBot Enterprise:</p>
<div style="margin:24px 0;padding:20px;text-align:center;background:#0d1116;border:1px solid #373d46;border-radius:16px;color:#e4c78f;font-size:34px;font-weight:700;letter-spacing:10px">{safe_code}</div>
<p style="margin:0;color:#c8c1b5;font-size:14px;line-height:1.55">Код действует 60 минут и может быть использован только один раз.</p>
<p style="margin:20px 0 0;color:#8f897f;font-size:13px;line-height:1.5">Если вы не запрашивали код, просто проигнорируйте это письмо. Никому не сообщайте код доступа.</p>
</td></tr></table>
</td></tr></table></body></html>'''

    async def request_code(self, email: str) -> bool:
        account = await self.session.scalar(
            select(Account).where(
                func.lower(Account.email) == email,
                Account.is_active.is_(True),
                Account.registered.is_(True),
            )
        )
        mail = await self.session.get(MailSettings, 1)
        if account is None or mail is None or not mail.is_active:
            return False

        current_time = self._now()
        latest = await self.session.scalar(
            select(PasswordAccessCode)
            .where(PasswordAccessCode.account_id == account.id)
            .order_by(PasswordAccessCode.created_at.desc())
            .limit(1)
        )
        if latest is not None and latest.created_at > current_time - self.RESEND_DELAY:
            return False

        await self.session.execute(
            update(PasswordAccessCode)
            .where(
                PasswordAccessCode.account_id == account.id,
                PasswordAccessCode.used_at.is_(None),
            )
            .values(used_at=current_time)
        )
        code = f"{secrets.randbelow(1_000_000):06d}"
        challenge = PasswordAccessCode(
            account_id=account.id,
            code_hash=self._hash_code(account.id, code),
            expires_at=current_time + self.CODE_TTL,
            attempts=0,
        )
        self.session.add(challenge)
        await self.session.flush()
        await WebIdentityService(self.session).send_email(
            recipient=email,
            subject="Одноразовый код доступа — SupportBot Enterprise",
            text=(
                f"Здравствуйте, {account.full_name}!\n\n"
                f"Ваш одноразовый код доступа: {code}\n\n"
                "Код действует 60 минут и может быть использован только один раз.\n"
                "Если вы не запрашивали код, проигнорируйте это письмо."
            ),
            html=self._email_html(account.full_name, code),
        )
        return True

    async def verify_code(self, email: str, code: str) -> tuple[Account, str] | None:
        account = await self.session.scalar(
            select(Account).where(
                func.lower(Account.email) == email,
                Account.is_active.is_(True),
                Account.registered.is_(True),
            )
        )
        if account is None:
            return None

        current_time = self._now()
        challenge = await self.session.scalar(
            select(PasswordAccessCode)
            .where(
                PasswordAccessCode.account_id == account.id,
                PasswordAccessCode.used_at.is_(None),
                PasswordAccessCode.expires_at > current_time,
            )
            .order_by(PasswordAccessCode.created_at.desc())
            .with_for_update()
            .limit(1)
        )
        if challenge is None:
            return None

        challenge.attempts += 1
        supplied_hash = self._hash_code(account.id, code)
        if not secrets.compare_digest(supplied_hash, challenge.code_hash):
            if challenge.attempts >= self.MAX_ATTEMPTS:
                challenge.used_at = current_time
            await self.session.commit()
            return None

        challenge.used_at = current_time
        reset_token = secrets.token_urlsafe(32)
        challenge.reset_token_hash = self._hash_reset_token(reset_token)
        challenge.reset_token_expires_at = current_time + self.RESET_TOKEN_TTL
        await self.session.execute(
            update(PasswordAccessCode)
            .where(
                PasswordAccessCode.account_id == account.id,
                PasswordAccessCode.id != challenge.id,
                PasswordAccessCode.used_at.is_(None),
            )
            .values(used_at=current_time)
        )
        await self.session.commit()
        return account, reset_token

    async def set_new_password(self, token: str, password: str) -> Account | None:
        current_time = self._now()
        token_hash = self._hash_reset_token(token)
        challenge = await self.session.scalar(
            select(PasswordAccessCode)
            .where(
                PasswordAccessCode.reset_token_hash == token_hash,
                PasswordAccessCode.reset_token_expires_at > current_time,
                PasswordAccessCode.password_changed_at.is_(None),
            )
            .with_for_update()
        )
        if challenge is None:
            return None

        account = await self.session.get(Account, challenge.account_id)
        if account is None or not account.is_active or not account.registered:
            return None

        account.password_hash = WebIdentityService.hash_password(password)
        account.email_verified_at = account.email_verified_at or current_time
        account.last_login = current_time
        challenge.password_changed_at = current_time
        challenge.reset_token_hash = None
        challenge.reset_token_expires_at = None
        await self.session.commit()
        return account
