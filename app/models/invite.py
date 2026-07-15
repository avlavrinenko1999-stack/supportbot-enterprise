from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import InviteRole
from app.models.mixins import IDMixin, TimestampMixin

class Invite(Base, IDMixin, TimestampMixin):
    """
    Одноразовое приглашение.
    В базе хранится только SHA-256 хэш токена.
    Сам токен попадает только в ссылку.
    """

    __tablename__ = "invites"

    token_hash: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[InviteRole] = mapped_column(
        Enum(InviteRole),
        nullable=False,
    )

    organizational_unit_id: Mapped[int] = mapped_column(
        ForeignKey(
            "organizational_units.id",
        ),
        nullable=False,
        index=True,
    )

    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    used_by_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    business_unit = relationship(
        "OrganizationalUnit",
        back_populates="invites",
    )

    created_by = relationship(
        "Account",
        foreign_keys=[created_by_id],
        back_populates="invites",
    )

    used_by = relationship(
        "Account",
        foreign_keys=[used_by_account_id],
        back_populates="used_invites",
    )

    repr_cols = (
        "id",
        "full_name",
        "role",
        "organizational_unit_id",
        "is_active",
    )
