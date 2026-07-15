from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.category import Category
from app.services.category_service import (
    CategoryDeleteResult,
    CategoryService,
)


def make_session() -> MagicMock:
    session = MagicMock()
    session.scalar = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.add = MagicMock()
    return session


def make_category(
    *,
    category_id: int = 10,
    company_id: int | None = 1,
    business_unit_id: int = 101,
    parent_id: int | None = None,
    name: str = "Поддержка",
    is_active: bool = True,
    is_archived: bool = False,
) -> Category:
    return Category(
        id=category_id,
        company_id=company_id,
        business_unit_id=business_unit_id,
        parent_id=parent_id,
        name=name,
        is_active=is_active,
        is_archived=is_archived,
    )


def test_category_service_contract() -> None:
    required_methods = {
        "get_category",
        "get_category_stats",
        "create_category",
        "rename_category",
        "archive_category",
        "restore_category",
        "delete_category",
    }

    for method_name in required_methods:
        assert hasattr(
            CategoryService,
            method_name,
        )


@pytest.mark.asyncio
async def test_create_category() -> None:
    session = make_session()
    session.scalar.side_effect = [
        101,
        SimpleNamespace(
            id=101,
            is_active=True,
        ),
        None,
    ]

    service = CategoryService(session)

    category = await service.create_category(
        company_id=1,
        name="  Техническая поддержка  ",
    )

    assert category.company_id is None
    assert category.parent_id is None
    assert category.name == "Техническая поддержка"
    assert category.is_active is True
    assert category.is_archived is False

    session.add.assert_called_once_with(category)
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(
        category
    )


@pytest.mark.asyncio
async def test_create_category_rejects_short_name() -> None:
    session = make_session()
    session.scalar.side_effect = [
        101,
        SimpleNamespace(
            id=101,
            is_active=True,
        ),
    ]

    service = CategoryService(session)

    with pytest.raises(
        ValueError,
        match="слишком короткое",
    ):
        await service.create_category(
            company_id=1,
            name="X",
        )

    session.add.assert_not_called()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_category_requires_active_company() -> None:
    session = make_session()
    session.scalar.return_value = None

    service = CategoryService(session)

    with pytest.raises(
        ValueError,
        match="рабочее подразделение",
    ):
        await service.create_category(
            company_id=999,
            name="Поддержка",
        )

    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_create_child_rejects_other_company() -> None:
    session = make_session()
    parent = make_category(
        category_id=5,
        company_id=2,
        business_unit_id=202,
    )

    session.scalar.side_effect = [
        101,
        SimpleNamespace(
            id=101,
            is_active=True,
        ),
        parent,
    ]

    service = CategoryService(session)

    with pytest.raises(
        ValueError,
        match=(
            "Родительская категория принадлежит "
            "другому рабочему подразделению"
        ),
    ):
        await service.create_category(
            company_id=1,
            parent_id=5,
            name="Подкатегория",
        )

    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_create_child_rejects_archived_parent() -> None:
    session = make_session()
    parent = make_category(
        category_id=5,
        company_id=1,
        is_active=False,
        is_archived=True,
    )

    session.scalar.side_effect = [
        101,
        SimpleNamespace(
            id=101,
            is_active=True,
        ),
        parent,
    ]

    service = CategoryService(session)

    with pytest.raises(
        ValueError,
        match="внутри архивной категории",
    ):
        await service.create_category(
            company_id=1,
            parent_id=5,
            name="Подкатегория",
        )

    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_create_category_rejects_duplicate() -> None:
    session = make_session()
    existing = make_category(
        category_id=7,
        company_id=1,
        name="Поддержка",
    )

    session.scalar.side_effect = [
        101,
        SimpleNamespace(
            id=101,
            is_active=True,
        ),
        existing,
    ]

    service = CategoryService(session)

    with pytest.raises(
        ValueError,
        match="уже существует",
    ):
        await service.create_category(
            company_id=1,
            name="Поддержка",
        )

    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_rename_category() -> None:
    session = make_session()
    category = make_category()

    session.scalar.side_effect = [
        category,
        None,
    ]

    service = CategoryService(session)

    result = await service.rename_category(
        category_id=category.id,
        new_name="  Новое название  ",
    )

    assert result is category
    assert category.name == "Новое название"

    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(
        category
    )


@pytest.mark.asyncio
async def test_rename_category_rejects_duplicate() -> None:
    session = make_session()
    category = make_category()
    duplicate = make_category(
        category_id=11,
        name="Новая категория",
    )

    session.scalar.side_effect = [
        category,
        duplicate,
    ]

    service = CategoryService(session)

    with pytest.raises(
        ValueError,
        match="уже существует",
    ):
        await service.rename_category(
            category_id=category.id,
            new_name="Новая категория",
        )

    assert category.name == "Поддержка"
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_archive_category() -> None:
    session = make_session()
    category = make_category()

    session.scalar.return_value = category

    service = CategoryService(session)

    result = await service.archive_category(
        category.id
    )

    assert result is category
    assert category.is_archived is True
    assert category.is_active is False

    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(
        category
    )


@pytest.mark.asyncio
async def test_restore_category() -> None:
    session = make_session()
    category = make_category(
        is_active=False,
        is_archived=True,
    )

    session.scalar.side_effect = [
        category,
        None,
    ]

    service = CategoryService(session)

    result = await service.restore_category(
        category.id
    )

    assert result is category
    assert category.is_archived is False
    assert category.is_active is True

    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(
        category
    )


@pytest.mark.asyncio
async def test_restore_category_rejects_duplicate() -> None:
    session = make_session()
    category = make_category(
        is_active=False,
        is_archived=True,
    )
    duplicate = make_category(
        category_id=12,
    )

    session.scalar.side_effect = [
        category,
        duplicate,
    ]

    service = CategoryService(session)

    with pytest.raises(
        ValueError,
        match="Нельзя восстановить категорию",
    ):
        await service.restore_category(
            category.id
        )

    assert category.is_archived is True
    assert category.is_active is False

    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_category_with_children() -> None:
    session = make_session()
    category = make_category()

    session.scalar.side_effect = [
        category,
        2,
    ]

    service = CategoryService(session)

    result = await service.delete_category(
        category.id
    )

    assert (
        result
        == CategoryDeleteResult.HAS_CHILDREN
    )

    session.delete.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_category_with_tickets() -> None:
    session = make_session()
    category = make_category()

    session.scalar.side_effect = [
        category,
        0,
        3,
    ]

    service = CategoryService(session)

    result = await service.delete_category(
        category.id
    )

    assert (
        result
        == CategoryDeleteResult.HAS_TICKETS
    )

    session.delete.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_empty_category() -> None:
    session = make_session()
    category = make_category()

    session.scalar.side_effect = [
        category,
        0,
        0,
    ]

    service = CategoryService(session)

    result = await service.delete_category(
        category.id
    )

    assert result == CategoryDeleteResult.DELETED

    session.delete.assert_awaited_once_with(
        category
    )
    session.commit.assert_awaited_once()
