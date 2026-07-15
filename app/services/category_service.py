from dataclasses import dataclass
from enum import Enum

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.legacy_company_mapping import (
    LegacyCompanyMapping,
)
from app.models.organizational_unit import (
    OrganizationalUnit,
)
from app.models.ticket import Ticket


class CategoryDeleteResult(str, Enum):
    DELETED = "deleted"
    HAS_TICKETS = "has_tickets"
    HAS_CHILDREN = "has_children"


@dataclass(frozen=True)
class CategoryWithStats:
    category: Category
    tickets_count: int
    children_count: int


class CategoryService:
    """
    Управление категориями рабочего подразделения.

    business_unit_id является канонической областью
    категории.

    create_category с company_id временно сохранён для старого UI
    и преобразует Company через LegacyCompanyMapping.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_active_for_business_unit(
        self,
        business_unit_id: int,
    ) -> list[Category]:
        return list(
            await self.session.scalars(
                select(Category)
                .where(
                    Category.business_unit_id
                    == business_unit_id,
                    Category.is_archived.is_(False),
                    Category.is_active.is_(True),
                )
                .order_by(Category.id)
            )
        )

    async def list_archived_for_business_unit(
        self,
        business_unit_id: int,
    ) -> list[Category]:
        return list(
            await self.session.scalars(
                select(Category)
                .where(
                    Category.business_unit_id
                    == business_unit_id,
                    Category.is_archived.is_(True),
                )
                .order_by(Category.id)
            )
        )

    async def get_category(
        self,
        category_id: int,
    ) -> Category | None:
        return await self.session.scalar(
            select(Category).where(
                Category.id == category_id
            )
        )

    async def get_category_stats(
        self,
        category_id: int,
    ) -> CategoryWithStats:
        category = await self.get_category(
            category_id
        )

        if category is None:
            raise ValueError(
                "Категория не найдена."
            )

        tickets_count = await self.session.scalar(
            select(func.count(Ticket.id)).where(
                Ticket.category_id == category_id
            )
        )

        children_count = await self.session.scalar(
            select(func.count(Category.id)).where(
                Category.parent_id == category_id
            )
        )

        return CategoryWithStats(
            category=category,
            tickets_count=tickets_count or 0,
            children_count=children_count or 0,
        )

    async def create_for_business_unit(
        self,
        *,
        business_unit_id: int,
        name: str,
        parent_id: int | None = None,
    ) -> Category:
        business_unit = await self.session.scalar(
            select(OrganizationalUnit).where(
                OrganizationalUnit.id
                == business_unit_id,
                OrganizationalUnit.is_active.is_(
                    True
                ),
            )
        )

        if business_unit is None:
            raise ValueError(
                "Рабочее подразделение не найдено "
                "или отключено."
            )

        clean_name = name.strip()

        if len(clean_name) < 2:
            raise ValueError(
                "Название категории слишком короткое."
            )

        if parent_id is not None:
            parent = await self.get_category(
                parent_id
            )

            if parent is None:
                raise ValueError(
                    "Родительская категория не найдена."
                )

            if (
                parent.business_unit_id
                != business_unit_id
            ):
                raise ValueError(
                    "Родительская категория принадлежит "
                    "другому рабочему подразделению."
                )

            if parent.is_archived:
                raise ValueError(
                    "Нельзя создать подкатегорию "
                    "внутри архивной категории."
                )

        duplicate = await self.session.scalar(
            select(Category).where(
                Category.business_unit_id
                == business_unit_id,
                Category.parent_id == parent_id,
                func.lower(Category.name)
                == clean_name.lower(),
                Category.is_archived.is_(False),
            )
        )

        if duplicate is not None:
            raise ValueError(
                "Активная категория с таким названием "
                "уже существует."
            )

        category = Category(
            business_unit_id=business_unit_id,
            parent_id=parent_id,
            name=clean_name,
            is_active=True,
            is_archived=False,
        )

        self.session.add(category)
        await self.session.commit()
        await self.session.refresh(category)

        return category

    async def create_category(
        self,
        *,
        company_id: int,
        name: str,
        parent_id: int | None = None,
    ) -> Category:
        """
        Временный адаптер старого Company UI.
        """
        business_unit_id = (
            await self._require_business_unit_id(
                company_id
            )
        )

        return await self.create_for_business_unit(
            business_unit_id=business_unit_id,
            name=name,
            parent_id=parent_id,
        )

    async def rename_category(
        self,
        *,
        category_id: int,
        new_name: str,
    ) -> Category:
        category = await self.get_category(
            category_id
        )

        if category is None:
            raise ValueError(
                "Категория не найдена."
            )

        clean_name = new_name.strip()

        if len(clean_name) < 2:
            raise ValueError(
                "Название категории слишком короткое."
            )

        duplicate = await self.session.scalar(
            select(Category).where(
                Category.business_unit_id
                == category.business_unit_id,
                Category.parent_id
                == category.parent_id,
                Category.id != category.id,
                func.lower(Category.name)
                == clean_name.lower(),
                Category.is_archived.is_(False),
            )
        )

        if duplicate is not None:
            raise ValueError(
                "Активная категория с таким названием "
                "уже существует."
            )

        category.name = clean_name

        await self.session.commit()
        await self.session.refresh(category)

        return category

    async def archive_category(
        self,
        category_id: int,
    ) -> Category:
        category = await self.get_category(
            category_id
        )

        if category is None:
            raise ValueError(
                "Категория не найдена."
            )

        category.is_archived = True
        category.is_active = False

        await self.session.commit()
        await self.session.refresh(category)

        return category

    async def restore_category(
        self,
        category_id: int,
    ) -> Category:
        category = await self.get_category(
            category_id
        )

        if category is None:
            raise ValueError(
                "Категория не найдена."
            )

        duplicate = await self.session.scalar(
            select(Category).where(
                Category.business_unit_id
                == category.business_unit_id,
                Category.parent_id
                == category.parent_id,
                Category.id != category.id,
                func.lower(Category.name)
                == category.name.lower(),
                Category.is_archived.is_(False),
            )
        )

        if duplicate is not None:
            raise ValueError(
                "Нельзя восстановить категорию: "
                "активная категория с таким названием "
                "уже существует."
            )

        category.is_archived = False
        category.is_active = True

        await self.session.commit()
        await self.session.refresh(category)

        return category

    async def delete_category(
        self,
        category_id: int,
    ) -> CategoryDeleteResult:
        category = await self.get_category(
            category_id
        )

        if category is None:
            raise ValueError(
                "Категория не найдена."
            )

        children_count = await self.session.scalar(
            select(func.count(Category.id)).where(
                Category.parent_id == category_id
            )
        )

        if children_count and children_count > 0:
            return CategoryDeleteResult.HAS_CHILDREN

        tickets_count = await self.session.scalar(
            select(func.count(Ticket.id)).where(
                Ticket.category_id == category_id
            )
        )

        if tickets_count and tickets_count > 0:
            return CategoryDeleteResult.HAS_TICKETS

        await self.session.delete(category)
        await self.session.commit()

        return CategoryDeleteResult.DELETED

    async def _require_business_unit_id(
        self,
        company_id: int,
    ) -> int:
        business_unit_id = await self.session.scalar(
            select(
                LegacyCompanyMapping
                .organizational_unit_id
            ).where(
                LegacyCompanyMapping.company_id
                == company_id
            )
        )

        if business_unit_id is None:
            raise ValueError(
                "Для компании не найдено рабочее "
                "подразделение."
            )

        return business_unit_id
