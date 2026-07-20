from app.ui.reply import build_reply_rows, reply_keyboard


def keyboard_rows(markup) -> list[list[str]]:
    return [
        [button.text for button in row]
        for row in markup.keyboard
    ]


def test_actions_are_paired_and_navigation_is_full_width() -> None:
    markup = reply_keyboard(
        [
            "Организации",
            "Холдинги",
            "Сотрудники",
            "Тикеты",
            "⬅️ Назад",
        ]
    )

    assert keyboard_rows(markup) == [
        ["Организации", "Холдинги"],
        ["Сотрудники", "Тикеты"],
        ["⬅️ Назад"],
    ]


def test_selectable_entities_remain_full_width() -> None:
    assert build_reply_rows(
        [
            "🏗 Продажи",
            "🏗 Маркетинг",
            "➕ Создать подразделение",
            "🔎 Найти подразделение",
            "⬅️ Каталог организаций",
        ]
    ) == [
        ["🏗 Продажи"],
        ["🏗 Маркетинг"],
        ["➕ Создать подразделение", "🔎 Найти подразделение"],
        ["⬅️ Каталог организаций"],
    ]


def test_long_actions_are_not_squeezed_into_two_columns() -> None:
    assert build_reply_rows(
        [
            "➕ Создать нижестоящее подразделение",
            "✏️ Переименовать подразделение",
            "📝 Изменить описание",
        ]
    ) == [
        ["➕ Создать нижестоящее подразделение"],
        ["✏️ Переименовать подразделение", "📝 Изменить описание"],
    ]
