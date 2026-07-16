from pathlib import Path


HANDLER_PATH = Path(
    "app/handlers/admin/company/links.py"
)


def test_company_links_use_business_unit_context() -> None:
    source = HANDLER_PATH.read_text(encoding="utf-8")

    assert (
        "_get_business_unit_id_or_answer"
        in source
    )
    assert "_get_company_id_or_answer" not in source
    assert "UIContext.get_business_unit_id" in source
    assert "UIContext.get_company_id" not in source
    assert "business_unit_id" in source
    assert "company_id" not in source


def test_company_link_stubs_name_business_unit() -> None:
    source = HANDLER_PATH.read_text(encoding="utf-8")

    assert "Координаторы подразделения" in source
    assert "Операторы подразделения" in source
    assert "Пользователи подразделения" in source
    assert "Сотрудники подразделения" in source
    assert "Тикеты подразделения" in source
    assert "Настройки подразделения" in source
