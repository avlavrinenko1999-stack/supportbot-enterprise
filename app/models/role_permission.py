from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IDMixin, TimestampMixin


class RolePermission(Base, IDMixin, TimestampMixin):
    """
    Разрешение, включённое в роль.

    На первом этапе поддерживается только ALLOW-модель.
    """

    __tablename__ = "role_permissions"

    role_id: Mapped[int] = mapped_column(
        ForeignKey(
            "roles.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    permission_id: Mapped[int] = mapped_column(
        ForeignKey(
            "permissions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    role = relationship(
        "Role",
        back_populates="permission_links",
    )

    permission = relationship(
        "PermissionDefinition",
        back_populates="role_links",
    )

    __table_args__ = (
        UniqueConstraint(
            "role_id",
            "permission_id",
            name="uq_role_permissions_role_permission",
        ),
    )

    repr_cols = (
        "id",
        "role_id",
        "permission_id",
    )
