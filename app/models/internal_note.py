from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IDMixin, TimestampMixin


class InternalNote(Base, IDMixin, TimestampMixin):
    """
    Внутренний комментарий сотрудников.
    """

    __tablename__ = "internal_notes"

    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False
    )

    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=False
    )

    body: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    ticket = relationship(
        "Ticket",
        back_populates="internal_notes"
    )

    author = relationship(
        "Account",
        back_populates="internal_notes"
    )

    repr_cols = (
        "id",
        "ticket_id",
        "account_id",
    )
