from sqlalchemy import Enum, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ScopeType
from app.models.mixins import IDMixin, TimestampMixin


class AccessAuditEvent(Base, IDMixin, TimestampMixin):
    """Событие изменения ролевого доступа."""

    __tablename__ = "access_audit_events"

    event_type: Mapped[str] = mapped_column(
        String(64),
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

    target_account_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "accounts.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    role_assignment_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "role_assignments.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    role_code: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    scope_type: Mapped[ScopeType | None] = mapped_column(
        Enum(
            ScopeType,
            name="access_audit_scope_type",
            native_enum=False,
            create_constraint=True,
            length=32,
        ),
        nullable=True,
        index=True,
    )

    scope_id: Mapped[int | None] = mapped_column(
        nullable=True,
        index=True,
    )

    details: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    actor = relationship(
        "Account",
        foreign_keys=[actor_account_id],
        back_populates="access_audit_events_created",
    )

    target_account = relationship(
        "Account",
        foreign_keys=[target_account_id],
        back_populates="access_audit_events_received",
    )

    role_assignment = relationship(
        "RoleAssignment",
        back_populates="audit_events",
    )

    repr_cols = (
        "id",
        "event_type",
        "actor_account_id",
        "target_account_id",
    )
