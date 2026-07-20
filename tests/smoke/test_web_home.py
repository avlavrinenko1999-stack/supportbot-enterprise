from pathlib import Path

from app.keyboards.admin import admin_main_menu


HOME_PAGE = (
    Path(__file__).resolve().parents[2]
    / "web"
    / "static"
    / "index.html"
)


def test_web_home_contains_bot_main_menu_sections() -> None:
    html = HOME_PAGE.read_text(encoding="utf-8")
    bot_buttons = [
        button.text
        for row in admin_main_menu().keyboard
        for button in row
    ]

    for button in bot_buttons:
        assert f'data-section="{button}"' in html


def test_web_home_has_launchpad_grid_and_no_section_links() -> None:
    html = HOME_PAGE.read_text(encoding="utf-8")

    assert 'class="app-grid"' in html
    assert "<a " not in html
    assert html.count('class="app"') == 8
