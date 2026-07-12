from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IDMixin, TimestampMixin


class Role(Base, IDMixin, TimestampMixin):
    """
    Шаблон набора разрешений.

    На текущем этапе модель не заменяет Account.role.
    """

    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )

    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    permission_links = relationship(
        "RolePermission",
        back_populates="role",
        cascade="all, delete-orphan",
    )

    assignments = relationship(
        "RoleAssignment",
        back_populates="role",
        cascade="all, delete-orphan",
    )

    repr_cols = (
        "id",
        "code",
        "name",
    )
