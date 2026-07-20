from io import BytesIO
from types import SimpleNamespace

from app.services.company_structure_pdf_service import (
    CompanyStructurePdfService,
)


def unit(
    unit_id: int,
    parent_id: int | None,
    name: str,
):
    owner = SimpleNamespace(full_name="Иван Руководитель")
    employee = SimpleNamespace(
        account=SimpleNamespace(full_name="Анна Сотрудник"),
        account_id=2,
        position_name=None,
        is_active=True,
    )
    deputy = SimpleNamespace(
        account=SimpleNamespace(full_name="Пётр Заместитель"),
        account_id=3,
        position_name="Заместитель руководителя",
        is_active=True,
    )
    return SimpleNamespace(
        id=unit_id,
        parent_id=parent_id,
        name=name,
        description="Функции подразделения",
        owner=owner,
        owner_account_id=1,
        account_memberships=[employee, deputy],
    )


def test_bitrix_style_structure_tree_is_recursive() -> None:
    roots = CompanyStructurePdfService._build_tree(
        [
            unit(1, None, "Компания"),
            unit(2, 1, "Продажи"),
            unit(3, 2, "Корпоративные продажи"),
        ]
    )
    CompanyStructurePdfService._layout(roots)

    assert roots[0].children[0].children[0].name == (
        "Корпоративные продажи"
    )
    assert roots[0].children[0].deputies == [
        "Пётр Заместитель"
    ]
    assert roots[0].children[0].employees == [
        "Анна Сотрудник"
    ]
    assert roots[0].children[0].y > roots[0].y


def test_structure_pdf_is_generated_in_memory() -> None:
    target = BytesIO()
    CompanyStructurePdfService._draw_pdf(
        target,
        "Тестовая организация",
        CompanyStructurePdfService._build_tree(
            [unit(1, None, "Отдел")]
        ),
    )

    assert target.getvalue().startswith(b"%PDF-")


def test_stale_file_limit_is_thirty_minutes() -> None:
    assert (
        CompanyStructurePdfService.MAX_FILE_AGE_SECONDS
        == 30 * 60
    )
