from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IDMixin, TimestampMixin


class LegalEntity(Base, IDMixin, TimestampMixin):
    """
    Юридическое лицо.

    Здесь хранятся только юридические и регистрационные
    реквизиты. Сотрудники, тикеты и рабочие настройки
    принадлежат OrganizationalUnit.
    """

    __tablename__ = "legal_entities"

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey(
            "tenants.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    legal_name: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    inn: Mapped[str | None] = mapped_column(
        String(12),
        nullable=True,
    )

    kpp: Mapped[str | None] = mapped_column(
        String(9),
        nullable=True,
    )

    ogrn: Mapped[str | None] = mapped_column(
        String(15),
        nullable=True,
    )

    legal_address: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )

    legal_status: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    legal_status_code: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    registration_date: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    liquidation_date: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    last_registry_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    tenant = relationship(
        "Tenant",
        back_populates="legal_entities",
    )

    organizational_units = relationship(
        "OrganizationalUnit",
        back_populates="legal_entity",
        cascade="all, delete-orphan",
        overlaps="children,parent,tenant",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_legal_entities_tenant_id_id",
        ),
        Index(
            "uq_legal_entities_tenant_inn",
            "tenant_id",
            "inn",
            unique=True,
            postgresql_where=text("inn IS NOT NULL"),
        ),
        Index(
            "uq_legal_entities_tenant_ogrn",
            "tenant_id",
            "ogrn",
            unique=True,
            postgresql_where=text("ogrn IS NOT NULL"),
        ),
    )

    repr_cols = (
        "id",
        "tenant_id",
        "name",
        "inn",
        "is_active",
    )
