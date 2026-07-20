import pytest

from app.models.account import Account
from app.models.invite import Invite
from app.models.enums import InviteRole
from app.models.mail_settings import MailSettings
from app.services.web_identity_service import WebIdentityService


def test_account_supports_email_identity_without_telegram() -> None:
    assert Account.__table__.c.telegram_id.nullable
    assert Account.__table__.c.email.nullable
    assert Account.__table__.c.email.unique
    assert Account.__table__.c.password_hash.nullable
    assert Account.__table__.c.email_verified_at.nullable


def test_invite_supports_email_delivery() -> None:
    assert Invite.__table__.c.email.nullable
    assert not Invite.__table__.c.delivery_channel.nullable
    assert InviteRole.ADMIN.value == "admin"


def test_mail_password_round_trip_is_encrypted() -> None:
    encrypted = WebIdentityService.encrypt_secret("smtp-secret")

    assert encrypted != "smtp-secret"
    assert WebIdentityService.decrypt_secret(encrypted) == "smtp-secret"


def test_password_is_hashed_and_verified() -> None:
    password_hash = WebIdentityService.hash_password("StrongPass2026")

    assert "StrongPass2026" not in password_hash
    assert WebIdentityService.verify_password("StrongPass2026", password_hash)
    assert not WebIdentityService.verify_password("WrongPass2026", password_hash)


@pytest.mark.parametrize(
    "password",
    ["short1", "onlyletterslong", "1234567890"],
)
def test_weak_password_is_rejected(password: str) -> None:
    with pytest.raises(ValueError):
        WebIdentityService.hash_password(password)


def test_mail_settings_has_single_server_side_secret_field() -> None:
    assert MailSettings.__table__.c.smtp_password_encrypted.nullable
    assert "smtp_password" not in MailSettings.__table__.c
