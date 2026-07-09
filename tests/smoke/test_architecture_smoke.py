def test_project_imports():
    import bot

    assert bot is not None


def test_menu_actions_resolve_back():
    from app.ui.actions import MenuAction, resolve_menu_action

    assert resolve_menu_action("⬅️ Назад") == MenuAction.BACK
    assert resolve_menu_action("⬅️ Back") == MenuAction.BACK


def test_menu_actions_resolve_main_buttons():
    from app.ui.actions import MenuAction, resolve_menu_action

    assert resolve_menu_action("Компании") == MenuAction.COMPANIES
    assert resolve_menu_action("Сотрудники") == MenuAction.EMPLOYEES
    assert resolve_menu_action("🌐 Language") == MenuAction.LANGUAGE
