from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import TicketStatus
from app.models.mixins import IDMixin, TimestampMixin


class Ticket(Base, IDMixin, TimestampMixin):
    """
    Обращение пользователя.
    """

    __tablename__ = "tickets"

    business_unit_id: Mapped[int] = mapped_column(
        ForeignKey(
            "organizational_units.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=False
    )

    operator_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=True
    )

    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"),
        nullable=True
    )

    subject: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus),
        default=TicketStatus.NEW,
        nullable=False
    )

    business_unit = relationship(
        "OrganizationalUnit",
        back_populates="tickets",
    )

    author = relationship(
        "Account",
        foreign_keys=[account_id],
        back_populates="tickets"
    )

    operator = relationship(
        "Account",
        foreign_keys=[operator_id],
        back_populates="assigned_tickets"
    )

    category = relationship(
        "Category",
        back_populates="tickets"
    )

    messages = relationship(
        "Message",
        back_populates="ticket",
        cascade="all, delete-orphan"
    )
    events = relationship(
        "TicketEvent",
        back_populates="ticket",
        cascade="all, delete-orphan"
    )

    internal_notes = relationship(
        "InternalNote",
        back_populates="ticket",
        cascade="all, delete-orphan"
    )

    repr_cols = (
        "id",
        "subject",
        "status",
    )
