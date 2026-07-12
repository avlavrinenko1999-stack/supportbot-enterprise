from sqlalchemy import Boolean, Enum, ForeignKey, String
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

    companies = relationship(
        "Company",
        back_populates="organization",
    )

    repr_cols = (
        "id",
        "name",
        "organization_type",
    )
