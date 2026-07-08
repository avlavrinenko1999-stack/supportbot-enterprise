from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IDMixin, TimestampMixin


class CompanySetting(Base, IDMixin, TimestampMixin):
    """
    Настройки компании.
    """

    __tablename__ = "company_settings"

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    timezone: Mapped[str] = mapped_column(
        String(64),
        default="Europe/Moscow",
        nullable=False
    )

    max_attachment_size: Mapped[int] = mapped_column(
        Integer,
        default=20 * 1024 * 1024,
        nullable=False
    )

    auto_close_days: Mapped[int] = mapped_column(
        Integer,
        default=30,
        nullable=False
    )

    allow_email_notifications: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    company = relationship(
        "Company",
        back_populates="settings"
    )

    repr_cols = (
        "id",
        "company_id",
    )
