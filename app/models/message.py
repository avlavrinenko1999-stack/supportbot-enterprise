from sqlalchemy import Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IDMixin, TimestampMixin


class Message(Base, IDMixin, TimestampMixin):
    """
    Сообщение внутри обращения.
    """

    __tablename__ = "messages"

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

    is_internal: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    ticket = relationship(
        "Ticket",
        back_populates="messages"
    )

    author = relationship(
        "Account",
        back_populates="messages"
    )

    attachments = relationship(
        "Attachment",
        back_populates="message",
        cascade="all, delete-orphan"
    )

    repr_cols = (
        "id",
        "ticket_id",
        "account_id",
    )
