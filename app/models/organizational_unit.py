from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import OrganizationalUnitType
from app.models.mixins import IDMixin, TimestampMixin


class OrganizationalUnit(Base, IDMixin, TimestampMixin):
    """
    Элемент рабочей организационной структуры.

    Это может быть филиал, департамент, отдел, офис,
    завод, склад, сервисный центр или бизнес-юнит.
    """

    __tablename__ = "organizational_units"

    tenant_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    legal_entity_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    parent_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    unit_type: Mapped[OrganizationalUnitType] = mapped_column(
        Enum(
            OrganizationalUnitType,
            name="organizational_unit_type",
            native_enum=False,
            create_constraint=True,
            length=32,
        ),
        nullable=False,
        default=OrganizationalUnitType.GENERAL,
        index=True,
    )

    code: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    tenant = relationship(
        "Tenant",
        back_populates="organizational_units",
        overlaps=(
            "children,legal_entity,"
            "organizational_units,parent"
        ),
    )

    legal_entity = relationship(
        "LegalEntity",
        back_populates="organizational_units",
        overlaps=(
            "children,organizational_units,"
            "parent,tenant"
        ),
    )

    parent = relationship(
        "OrganizationalUnit",
        remote_side=(
            "OrganizationalUnit.tenant_id, "
            "OrganizationalUnit.legal_entity_id, "
            "OrganizationalUnit.id"
        ),
        back_populates="children",
        overlaps=(
            "legal_entity,organizational_units,"
            "tenant"
        ),
    )

    children = relationship(
        "OrganizationalUnit",
        back_populates="parent",
        cascade="all, delete-orphan",
        single_parent=True,
        overlaps=(
            "legal_entity,organizational_units,"
            "tenant"
        ),
    )

    account_memberships = relationship(
        "AccountOrganizationalUnitMembership",
        back_populates="organizational_unit",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "legal_entity_id",
            "id",
            name=(
                "uq_organizational_units_"
                "tenant_legal_entity_id"
            ),
        ),
        ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_organizational_units_tenant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "legal_entity_id"],
            [
                "legal_entities.tenant_id",
                "legal_entities.id",
            ],
            name=(
                "fk_organizational_units_"
                "tenant_legal_entity"
            ),
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            [
                "tenant_id",
                "legal_entity_id",
                "parent_id",
            ],
            [
                "organizational_units.tenant_id",
                "organizational_units.legal_entity_id",
                "organizational_units.id",
            ],
            name=(
                "fk_organizational_units_"
                "parent_same_legal_entity"
            ),
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "legal_entity_id",
            "parent_id",
            "name",
            name=(
                "uq_organizational_units_"
                "parent_name"
            ),
        ),
        Index(
            "ix_organizational_units_tree",
            "tenant_id",
            "legal_entity_id",
            "parent_id",
        ),
    )

    repr_cols = (
        "id",
        "tenant_id",
        "legal_entity_id",
        "parent_id",
        "name",
        "unit_type",
    )
