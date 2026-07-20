from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import OrganizationType
from app.models.mixins import IDMixin, TimestampMixin


class Organization(Base, IDMixin, TimestampMixin):
    """
    Самостоятельный участник системы.

    Организацией может быть владелец платформы, клиент,
    внешний поставщик поддержки или партнёр.
    """

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    organization_type: Mapped[OrganizationType] = mapped_column(
        Enum(
            OrganizationType,
            name="organization_type",
            native_enum=False,
            length=32,
        ),
        nullable=False,
    )

    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "organizations.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    legal_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    inn: Mapped[str | None] = mapped_column(String(12), unique=True, nullable=True)
    kpp: Mapped[str | None] = mapped_column(String(9), nullable=True)
    ogrn: Mapped[str | None] = mapped_column(String(15), nullable=True)
    legal_address: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    legal_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    legal_status_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    registration_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    liquidation_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_registry_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    parent = relationship(
        "Organization",
        remote_side="Organization.id",
        back_populates="children",
    )

    children = relationship(
        "Organization",
        back_populates="parent",
    )

    holdings = relationship(
        "Holding",
        back_populates="organization",
    )

    audit_events = relationship(
        "OrganizationAuditEvent",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    repr_cols = (
        "id",
        "name",
        "organization_type",
    )
