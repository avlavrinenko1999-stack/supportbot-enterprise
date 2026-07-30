import base64
import hashlib
import hmac
import json
import secrets
import struct
import time
from urllib.parse import quote

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.two_factor_setting import TwoFactorSetting
from app.services.web_identity_service import WebIdentityService


class TwoFactorService:
    PROVIDERS = {
        "yandex": "Яндекс Ключ",
        "microsoft": "Microsoft Authenticator",
        "google": "Google Authenticator",
    }
    PERIOD = 30
    DIGITS = 6
    WINDOW = 1
    RECOVERY_COUNT = 10
    RECOVERY_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def generate_secret() -> str:
        return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")

    @staticmethod
    def _decode_secret(secret: str) -> bytes:
        padding = "=" * ((8 - len(secret) % 8) % 8)
        return base64.b32decode(secret + padding, casefold=True)

    @classmethod
    def code_for_counter(cls, secret: str, counter: int) -> str:
        digest = hmac.new(
            cls._decode_secret(secret),
            struct.pack(">Q", counter),
            hashlib.sha1,
        ).digest()
        offset = digest[-1] & 0x0F
        value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
        return str(value % (10 ** cls.DIGITS)).zfill(cls.DIGITS)

    @classmethod
    def matching_counter(cls, secret: str, code: str) -> int | None:
        if len(code) != cls.DIGITS or not code.isdigit():
            return None
        current = int(time.time()) // cls.PERIOD
        for delta in range(-cls.WINDOW, cls.WINDOW + 1):
            candidate = current + delta
            if hmac.compare_digest(cls.code_for_counter(secret, candidate), code):
                return candidate
        return None

    @staticmethod
    def _hash_recovery_code(code: str) -> str:
        normalized = code.replace("-", "").strip().upper()
        return hmac.new(
            settings.SECRET_KEY.encode(),
            f"2fa-recovery:{normalized}".encode(),
            hashlib.sha256,
        ).hexdigest()

    @classmethod
    def generate_recovery_codes(cls) -> list[str]:
        codes = []
        for _ in range(cls.RECOVERY_COUNT):
            raw = "".join(secrets.choice(cls.RECOVERY_ALPHABET) for _ in range(8))
            codes.append(f"{raw[:4]}-{raw[4:]}")
        return codes

    @staticmethod
    def provisioning_uri(secret: str, email: str) -> str:
        label = quote(f"SupportBot Enterprise:{email}", safe="")
        issuer = quote("SupportBot Enterprise", safe="")
        return (
            f"otpauth://totp/{label}?secret={secret}&issuer={issuer}"
            "&algorithm=SHA1&digits=6&period=30"
        )

    async def get(self, account_id: int) -> TwoFactorSetting | None:
        return await self.session.get(TwoFactorSetting, account_id)

    async def start_enrollment(self, account_id: int, provider: str) -> TwoFactorSetting:
        if provider not in self.PROVIDERS:
            raise ValueError("Выберите приложение из списка.")
        setting = await self.get(account_id)
        secret = self.generate_secret()
        if setting is None:
            setting = TwoFactorSetting(
                account_id=account_id,
                provider=provider,
                secret_encrypted=WebIdentityService.encrypt_secret(secret),
                is_enabled=False,
            )
            self.session.add(setting)
        elif not setting.is_enabled:
            setting.provider = provider
            setting.secret_encrypted = WebIdentityService.encrypt_secret(secret)
            setting.last_used_counter = None
            setting.recovery_code_hashes = None
        else:
            raise ValueError("Двухфакторная аутентификация уже настроена.")
        await self.session.commit()
        return setting

    @staticmethod
    def secret(setting: TwoFactorSetting) -> str:
        return WebIdentityService.decrypt_secret(setting.secret_encrypted) or ""

    async def verify_enrollment(self, setting: TwoFactorSetting, code: str) -> bool:
        counter = self.matching_counter(self.secret(setting), code)
        if counter is None:
            return False
        setting.last_used_counter = counter
        await self.session.commit()
        return True

    async def activate(self, setting: TwoFactorSetting, recovery_codes: list[str], enabled_at) -> None:
        setting.recovery_code_hashes = json.dumps(
            [self._hash_recovery_code(code) for code in recovery_codes]
        )
        setting.is_enabled = True
        setting.enabled_at = enabled_at
        await self.session.commit()

    async def verify_login(self, setting: TwoFactorSetting, code: str) -> bool:
        normalized = code.strip().upper()
        counter = self.matching_counter(self.secret(setting), normalized)
        if counter is not None:
            if setting.last_used_counter is not None and counter <= setting.last_used_counter:
                return False
            setting.last_used_counter = counter
            await self.session.commit()
            return True

        supplied_hash = self._hash_recovery_code(normalized)
        hashes = json.loads(setting.recovery_code_hashes or "[]")
        for index, stored_hash in enumerate(hashes):
            if hmac.compare_digest(supplied_hash, stored_hash):
                hashes.pop(index)
                setting.recovery_code_hashes = json.dumps(hashes)
                await self.session.commit()
                return True
        return False

    async def verify_totp_only(self, setting: TwoFactorSetting, code: str) -> bool:
        """Verify a live application code; recovery codes are deliberately rejected."""
        normalized = code.strip()
        counter = self.matching_counter(self.secret(setting), normalized)
        if counter is None:
            return False
        if setting.last_used_counter is not None and counter <= setting.last_used_counter:
            return False
        setting.last_used_counter = counter
        await self.session.flush()
        return True
