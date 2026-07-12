from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ScopeType
from app.models.mixins import IDMixin, TimestampMixin


class RoleAssignment(Base, IDMixin, TimestampMixin):
    """
    Назначение роли аккаунту в определённой области действия.

    PLATFORM требует scope_id=None.
    Остальные области требуют положительный scope_id.
    """

    __tablename__ = "role_assignments"

    account_id: Mapped[int] = mapped_column(
        ForeignKey(
            "accounts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    role_id: Mapped[int] = mapped_column(
        ForeignKey(
            "roles.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    scope_type: Mapped[ScopeType] = mapped_column(
        Enum(
            ScopeType,
            name="access_scope_type",
            native_enum=False,
            create_constraint=True,
            length=32,
        ),
        nullable=False,
        index=True,
    )

    scope_id: Mapped[int | None] = mapped_column(
        nullable=True,
        index=True,
    )

    valid_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    valid_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    granted_by_account_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "accounts.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    grant_reason: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    revoked_by_account_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "accounts.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    account = relationship(
        "Account",
        foreign_keys=[account_id],
        back_populates="role_assignments",
    )

    role = relationship(
        "Role",
        back_populates="assignments",
    )

    granted_by = relationship(
        "Account",
        foreign_keys=[granted_by_account_id],
        back_populates="granted_role_assignments",
    )

    revoked_by = relationship(
        "Account",
        foreign_keys=[revoked_by_account_id],
        back_populates="revoked_role_assignments",
    )

    audit_events = relationship(
        "AccessAuditEvent",
        back_populates="role_assignment",
    )

    __table_args__ = (
        CheckConstraint(
            "("
            "scope_type = 'PLATFORM' AND scope_id IS NULL"
            ") OR ("
            "scope_type != 'PLATFORM' AND scope_id IS NOT NULL "
            "AND scope_id > 0"
            ")",
            name="ck_role_assignments_scope_consistency",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL "
            "OR valid_to > valid_from",
            name="ck_role_assignments_valid_period",
        ),
        CheckConstraint(
            "revoked_at IS NULL OR is_active = false",
            name="ck_role_assignments_revocation_state",
        ),
        Index(
            "ix_role_assignments_account_scope",
            "account_id",
            "scope_type",
            "scope_id",
        ),
        Index(
            "ix_role_assignments_active_period",
            "is_active",
            "valid_from",
            "valid_to",
        ),
    )

    repr_cols = (
        "id",
        "account_id",
        "role_id",
        "scope_type",
        "scope_id",
    )
