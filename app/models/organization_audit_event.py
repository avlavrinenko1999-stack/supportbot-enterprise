from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IDMixin, TimestampMixin


class OrganizationAuditEvent(
    Base,
    IDMixin,
    TimestampMixin,
):
    """Событие изменения организации."""

    __tablename__ = "organization_audit_events"

    organization_id: Mapped[int] = mapped_column(
        ForeignKey(
            "organizations.id",
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

    organization = relationship(
        "Organization",
        back_populates="audit_events",
    )

    actor = relationship("Account")

    repr_cols = (
        "id",
        "organization_id",
        "event_type",
        "actor_account_id",
    )
