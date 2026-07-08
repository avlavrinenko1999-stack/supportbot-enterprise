from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import UserRole
from app.models.mixins import IDMixin, TimestampMixin


class CategoryMember(Base, IDMixin, TimestampMixin):
    """
    Участник категории.

    Используется для назначения координаторов и операторов
    на конкретные категории компании.
    """

    __tablename__ = "category_members"

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
    )

    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    )

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        nullable=False,
    )

    category = relationship(
        "Category",
        back_populates="members",
    )

    account = relationship(
        "Account",
    )

    __table_args__ = (
        UniqueConstraint(
            "category_id",
            "account_id",
            "role",
            name="uq_category_members_category_account_role",
        ),
    )

    repr_cols = (
        "id",
        "category_id",
        "account_id",
        "role",
    )
