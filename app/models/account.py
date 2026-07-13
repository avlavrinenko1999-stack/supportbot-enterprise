from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import UserRole
from app.models.mixins import IDMixin, TimestampMixin


class Account(Base, IDMixin, TimestampMixin):
    """
    Пользователь системы.
    """

    __tablename__ = "accounts"

    telegram_id: Mapped[int | None] = mapped_column(
        BigInteger,
        unique=True,
        nullable=True
    )

    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        nullable=False
    )

    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id"),
        nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    registered: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    language: Mapped[str] = mapped_column(
        String(8),
        default="ru",
        nullable=False,
    )

    company = relationship(
        "Company",
        back_populates="accounts"
    )

    tickets = relationship(
        "Ticket",
        foreign_keys="Ticket.account_id",
        back_populates="author"
    )

    assigned_tickets = relationship(
        "Ticket",
        foreign_keys="Ticket.operator_id",
        back_populates="operator"
    )

    messages = relationship(
        "Message",
        back_populates="author"
    )

    internal_notes = relationship(
        "InternalNote",
        back_populates="author"
    )

    invites = relationship(
        "Invite",
        foreign_keys="Invite.created_by_id",
        back_populates="created_by"
    )

    used_invites = relationship(
        "Invite",
        foreign_keys="Invite.used_by_account_id",
        back_populates="used_by"
    )

    company_preferences = relationship(
        "AccountCompanyPreference",
        back_populates="account",
        cascade="all, delete-orphan",
    )

    organizational_unit_memberships = relationship(
        "AccountOrganizationalUnitMembership",
        back_populates="account",
        cascade="all, delete-orphan",
    )

    role_assignments = relationship(
        "RoleAssignment",
        foreign_keys="RoleAssignment.account_id",
        back_populates="account",
        cascade="all, delete-orphan",
    )

    granted_role_assignments = relationship(
        "RoleAssignment",
        foreign_keys="RoleAssignment.granted_by_account_id",
        back_populates="granted_by",
    )

    revoked_role_assignments = relationship(
        "RoleAssignment",
        foreign_keys="RoleAssignment.revoked_by_account_id",
        back_populates="revoked_by",
    )

    access_audit_events_created = relationship(
        "AccessAuditEvent",
        foreign_keys="AccessAuditEvent.actor_account_id",
        back_populates="actor",
    )

    access_audit_events_received = relationship(
        "AccessAuditEvent",
        foreign_keys="AccessAuditEvent.target_account_id",
        back_populates="target_account",
    )

    repr_cols = (
        "id",
        "full_name",
        "role",
    )
