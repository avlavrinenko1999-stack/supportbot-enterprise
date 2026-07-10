from typing import Any

import pytest

from app.services.message_service import MessageService
from app.ui.actions import MenuAction, resolve_menu_action
from app.ui.screen_presenter import ScreenPresenter
from app.ui.screen_response import ScreenResponse


def test_screen_response_defaults() -> None:
    response = ScreenResponse(text="Тестовый экран")

    assert response.text == "Тестовый экран"
    assert response.reply_markup is None
    assert response.delete_user_message is True
    assert response.message_kwargs == {}


def test_menu_actions_resolve_russian_buttons() -> None:
    expected = {
        "Компании": MenuAction.COMPANIES,
        "Сотрудники": MenuAction.EMPLOYEES,
        "Профиль": MenuAction.PROFILE,
        "🌐 Language": MenuAction.LANGUAGE,
        "⬅️ Назад": MenuAction.BACK,
        "➡️ Далее": MenuAction.NEXT,
        "Отмена": MenuAction.CANCEL,
    }

    for text, action in expected.items():
        assert resolve_menu_action(text) == action


def test_menu_actions_resolve_english_buttons() -> None:
    expected = {
        "Companies": MenuAction.COMPANIES,
        "Employees": MenuAction.EMPLOYEES,
        "Profile": MenuAction.PROFILE,
        "Language": MenuAction.LANGUAGE,
        "⬅️ Back": MenuAction.BACK,
        "Back": MenuAction.BACK,
        "Cancel": MenuAction.CANCEL,
        "Next": MenuAction.NEXT,
    }

    for text, action in expected.items():
        assert resolve_menu_action(text) == action


@pytest.mark.asyncio
async def test_screen_presenter_forwards_response_to_message_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    expected_result = object()

    async def fake_replace_service_message(
        message: Any,
        state: Any,
        text: str,
        *,
        delete_user_message: bool = True,
        **kwargs: Any,
    ) -> Any:
        captured.update(
            {
                "message": message,
                "state": state,
                "text": text,
                "delete_user_message": delete_user_message,
                "kwargs": kwargs,
            }
        )
        return expected_result

    monkeypatch.setattr(
        MessageService,
        "replace_service_message",
        fake_replace_service_message,
    )

    message = object()
    state = object()
    keyboard = object()

    response = ScreenResponse(
        text="Экран",
        reply_markup=keyboard,
        delete_user_message=False,
        message_kwargs={
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
    )

    result = await ScreenPresenter.show(message, state, response)

    assert result is expected_result
    assert captured["message"] is message
    assert captured["state"] is state
    assert captured["text"] == "Экран"
    assert captured["delete_user_message"] is False
    assert captured["kwargs"] == {
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "reply_markup": keyboard,
    }
