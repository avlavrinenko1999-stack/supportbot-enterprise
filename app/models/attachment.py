from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IDMixin, TimestampMixin


class Attachment(Base, IDMixin, TimestampMixin):
    """
    Вложение к сообщению.
    """

    __tablename__ = "attachments"

    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False
    )

    original_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    storage_name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False
    )

    mime_type: Mapped[str] = mapped_column(
        String(120),
        nullable=False
    )

    size: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    message = relationship(
        "Message",
        back_populates="attachments"
    )

    repr_cols = (
        "id",
        "original_name",
        "size",
    )
