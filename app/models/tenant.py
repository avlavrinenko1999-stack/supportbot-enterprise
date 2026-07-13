from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IDMixin, TimestampMixin


class Tenant(Base, IDMixin, TimestampMixin):
    """
    Изолированный контур данных клиента платформы.

    Tenant задаёт верхнюю границу безопасности,
    конфигурации, интеграций и лицензирования.
    """

    __tablename__ = "tenants"

    code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    legal_entities = relationship(
        "LegalEntity",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )

    organizational_units = relationship(
        "OrganizationalUnit",
        back_populates="tenant",
        cascade="all, delete-orphan",
        overlaps=(
            "children,legal_entity,"
            "organizational_units,parent"
        ),
    )

    repr_cols = (
        "id",
        "code",
        "name",
        "is_active",
    )
