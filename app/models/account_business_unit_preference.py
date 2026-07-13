from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IDMixin, TimestampMixin


class AccountBusinessUnitPreference(
    Base,
    IDMixin,
    TimestampMixin,
):
    """
    Пользовательские настройки рабочего подразделения.

    Предпочтение связано непосредственно с
    OrganizationalUnit и не зависит от legacy Company.
    """

    __tablename__ = (
        "account_business_unit_preferences"
    )

    account_id: Mapped[int] = mapped_column(
        ForeignKey(
            "accounts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    business_unit_id: Mapped[int] = mapped_column(
        ForeignKey(
            "organizational_units.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    is_favorite: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    last_opened_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    pin_order: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    account = relationship(
        "Account",
        back_populates=(
            "business_unit_preferences"
        ),
    )

    business_unit = relationship(
        "OrganizationalUnit",
        back_populates="account_preferences",
    )

    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "business_unit_id",
            name=(
                "uq_account_business_unit_"
                "preference"
            ),
        ),
        Index(
            "ix_account_business_unit_"
            "preferences_favorite",
            "account_id",
            "is_favorite",
        ),
        Index(
            "ix_account_business_unit_"
            "preferences_recent",
            "account_id",
            "last_opened_at",
        ),
    )

    repr_cols = (
        "id",
        "account_id",
        "business_unit_id",
        "is_favorite",
    )
