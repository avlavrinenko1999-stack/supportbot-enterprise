from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IDMixin, TimestampMixin


class PermissionDefinition(Base, IDMixin, TimestampMixin):
    """
    Конкретное разрешённое действие.

    Название класса не конфликтует с текущим enum
    app.security.permissions.Permission.
    """

    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(
        String(128),
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

    inherits_downward: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    role_links = relationship(
        "RolePermission",
        back_populates="permission",
        cascade="all, delete-orphan",
    )

    repr_cols = (
        "id",
        "code",
        "name",
    )
