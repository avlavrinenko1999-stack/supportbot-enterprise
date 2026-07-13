from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IDMixin, TimestampMixin


class AccountOrganizationalUnitMembership(
    Base,
    IDMixin,
    TimestampMixin,
):
    """
    Членство сотрудника в рабочем подразделении.

    Одно активное членство может быть основным.
    Остальные членства описывают матричную структуру,
    дополнительные функции и совместную работу.
    """

    __tablename__ = (
        "account_organizational_unit_memberships"
    )

    account_id: Mapped[int] = mapped_column(
        ForeignKey(
            "accounts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    organizational_unit_id: Mapped[int] = mapped_column(
        ForeignKey(
            "organizational_units.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    position_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    account = relationship(
        "Account",
        back_populates=(
            "organizational_unit_memberships"
        ),
    )

    organizational_unit = relationship(
        "OrganizationalUnit",
        back_populates="account_memberships",
    )

    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "organizational_unit_id",
            name=(
                "uq_account_organizational_unit_"
                "membership"
            ),
        ),
        Index(
            "uq_account_primary_organizational_unit",
            "account_id",
            unique=True,
            postgresql_where=text(
                "is_primary = true AND is_active = true"
            ),
        ),
        Index(
            "ix_aou_memberships_unit_id",
            "organizational_unit_id",
        ),
        Index(
            "ix_account_organizational_unit_active",
            "organizational_unit_id",
            "is_active",
        ),
    )

    repr_cols = (
        "id",
        "account_id",
        "organizational_unit_id",
        "is_primary",
        "is_active",
    )
