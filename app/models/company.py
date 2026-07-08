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

    inn: Mapped[str | None] = mapped_column(
        String(12),
        unique=True,
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

    legal_name: Mapped[str | None] = mapped_column(
        String(512),
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

    account_preferences = relationship(
        "AccountCompanyPreference",
        back_populates="company",
        cascade="all, delete-orphan",
    )

    repr_cols = (
        "id",
        "name",
        "is_active",
    )
