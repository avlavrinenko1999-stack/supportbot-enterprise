from sqlalchemy import Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import EventType
from app.models.mixins import IDMixin, TimestampMixin


class TicketEvent(Base, IDMixin, TimestampMixin):
    """
    История изменений обращения.
    """

    __tablename__ = "ticket_events"

    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False
    )

    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=True
    )

    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType),
        nullable=False
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    ticket = relationship(
        "Ticket",
        back_populates="events"
    )

    author = relationship(
        "Account"
    )

    repr_cols = (
        "id",
        "ticket_id",
        "event_type",
    )
