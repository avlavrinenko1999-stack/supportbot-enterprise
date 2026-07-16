
import pytest

from app.security.scope_resolvers import (
    company_scope_from_callback,
    company_scope_from_reply,
)


@pytest.mark.asyncio
async def test_company_scope_from_reply_button() -> None:
    from aiogram.types import Chat, Message, User

    event = Message(
        message_id=1,
        date=0,
        chat=Chat(id=1, type="private"),
        from_user=User(
            id=1,
            is_bot=False,
            first_name="Test",
        ),
        text="✅ 42. Test Company",
    )

    scope = await company_scope_from_reply(event, None)

    assert scope is not None
    assert scope.scope_id == 42


@pytest.mark.asyncio
async def test_company_scope_from_callback_data() -> None:
    from aiogram.types import CallbackQuery, User

    event = CallbackQuery(
        id="1",
        from_user=User(
            id=1,
            is_bot=False,
            first_name="Test",
        ),
        chat_instance="test",
        data="company:view:81",
    )

    scope = await company_scope_from_callback(event, None)

    assert scope is not None
    assert scope.scope_id == 81


def test_scope_resolvers_have_no_direct_legacy_model_dependency() -> None:
    from pathlib import Path

    source = Path(
        "app/security/scope_resolvers.py"
    ).read_text(encoding="utf-8")

    assert (
        "from app.models.legacy_company_mapping import"
        not in source
    )
    assert "LegacyCompanyMappingService" in source
