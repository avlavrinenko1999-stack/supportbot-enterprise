from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IDMixin, TimestampMixin


class AccountCompanyPreference(Base, IDMixin, TimestampMixin):
    __tablename__ = "account_company_preferences"

    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )

    is_favorite: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    last_opened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    pin_order: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    account = relationship("Account", back_populates="company_preferences")
    company = relationship("Company", back_populates="account_preferences")

    __table_args__ = (
        UniqueConstraint("account_id", "company_id", name="uq_account_company_preference"),
    )
