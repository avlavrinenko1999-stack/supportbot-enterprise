from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IDMixin, TimestampMixin


class Category(Base, IDMixin, TimestampMixin):
    """
    Категория обращений.
    Поддерживает древовидную структуру.
    """

    __tablename__ = "categories"

    business_unit_id: Mapped[int] = mapped_column(
        ForeignKey(
            "organizational_units.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=True
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    business_unit = relationship(
        "OrganizationalUnit",
        back_populates="categories",
    )

    parent = relationship(
        "Category",
        remote_side="Category.id",
        back_populates="children"
    )

    children = relationship(
        "Category",
        back_populates="parent",
        cascade="all, delete-orphan"
    )

    tickets = relationship(
        "Ticket",
        back_populates="category"
    )

    members = relationship(
        "CategoryMember",
        back_populates="category",
        cascade="all, delete-orphan"
    )

    repr_cols = (
        "id",
        "business_unit_id",
        "name",
        "is_active",
        "is_archived",
    )
