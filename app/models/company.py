from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IDMixin, TimestampMixin


class Company(Base, IDMixin, TimestampMixin):
    """
    Компания.
    """

    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    accounts = relationship(
        "Account",
        back_populates="company",
        cascade="all, delete-orphan"
    )

    invites = relationship(
        "Invite",
        back_populates="company",
        cascade="all, delete-orphan"
    )

    categories = relationship(
        "Category",
        back_populates="company",
        cascade="all, delete-orphan"
    )

    tickets = relationship(
        "Ticket",
        back_populates="company",
        cascade="all, delete-orphan"
    )

    settings = relationship(
        "CompanySetting",
        back_populates="company",
        uselist=False,
        cascade="all, delete-orphan"
    )

    repr_cols = (
        "id",
        "name",
        "is_active",
    )
