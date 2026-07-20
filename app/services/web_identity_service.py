import asyncio
import base64
import hashlib
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

import bcrypt
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.mail_settings import MailSettings


class WebIdentityService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def normalize_email(value: str | None) -> str:
        email = (value or "").strip().casefold()
        if (
            len(email) > 320
            or "@" not in email
            or email.startswith("@")
            or email.endswith("@")
        ):
            raise ValueError("Укажите корректный email.")
        return email

    @staticmethod
    def hash_password(password: str) -> str:
        WebIdentityService.validate_password(password)
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

    @staticmethod
    def verify_password(password: str, password_hash: str | None) -> bool:
        if not password_hash:
            return False
        try:
            return bcrypt.checkpw(password.encode(), password_hash.encode())
        except (ValueError, TypeError):
            return False

    @staticmethod
    def validate_password(password: str) -> None:
        if len(password) < 10:
            raise ValueError("Пароль должен содержать не менее 10 символов.")
        if not any(character.isalpha() for character in password):
            raise ValueError("Добавьте в пароль буквы.")
        if not any(character.isdigit() for character in password):
            raise ValueError("Добавьте в пароль цифры.")

    @staticmethod
    def _cipher() -> Fernet:
        key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(key))

    @classmethod
    def encrypt_secret(cls, value: str) -> str:
        return cls._cipher().encrypt(value.encode()).decode()

    @classmethod
    def decrypt_secret(cls, value: str | None) -> str | None:
        if not value:
            return None
        return cls._cipher().decrypt(value.encode()).decode()

    async def send_email(
        self,
        *,
        recipient: str,
        subject: str,
        text: str,
    ) -> None:
        mail = await self.session.get(MailSettings, 1)
        if mail is None or not mail.is_active:
            raise ValueError("Почтовый сервер ещё не настроен.")

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = formataddr((mail.from_name, mail.from_email))
        message["To"] = recipient
        message.set_content(text)
        password = self.decrypt_secret(mail.smtp_password_encrypted)

        def deliver() -> None:
            with smtplib.SMTP(mail.smtp_host, mail.smtp_port, timeout=20) as smtp:
                if mail.use_starttls:
                    smtp.starttls()
                if mail.smtp_username:
                    smtp.login(mail.smtp_username, password or "")
                smtp.send_message(message)

        await asyncio.to_thread(deliver)
