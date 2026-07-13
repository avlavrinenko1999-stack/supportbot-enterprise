from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IDMixin, TimestampMixin


class LegalEntityAuditEvent(
    Base,
    IDMixin,
    TimestampMixin,
):
    """Событие изменения карточки юридического лица."""

    __tablename__ = "legal_entity_audit_events"

    legal_entity_id: Mapped[int] = mapped_column(
        ForeignKey(
            "legal_entities.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    actor_account_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "accounts.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="system",
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    payload: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    legal_entity = relationship(
        "LegalEntity",
        back_populates="audit_events",
    )

    actor = relationship("Account")

    repr_cols = (
        "id",
        "legal_entity_id",
        "event_type",
        "actor_account_id",
    )
