from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IDMixin, TimestampMixin


class LegacyCompanyMapping(
    Base,
    IDMixin,
    TimestampMixin,
):
    """
    Переходное соответствие старой Company новой модели.

    Несколько Company могут относиться к одному LegalEntity,
    но каждая Company получает собственное корневое
    OrganizationalUnit.
    """

    __tablename__ = "legacy_company_mappings"

    company_id: Mapped[int] = mapped_column(
        ForeignKey(
            "companies.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
        index=True,
    )

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey(
            "tenants.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    legal_entity_id: Mapped[int] = mapped_column(
        ForeignKey(
            "legal_entities.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    organizational_unit_id: Mapped[int] = mapped_column(
        ForeignKey(
            "organizational_units.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
        index=True,
    )

    company = relationship("Company")
    tenant = relationship("Tenant")
    legal_entity = relationship("LegalEntity")
    organizational_unit = relationship(
        "OrganizationalUnit"
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "tenant_id",
            name="uq_legacy_company_mapping_company_tenant",
        ),
        Index(
            "ix_legacy_company_mapping_legal_entity",
            "legal_entity_id",
            "company_id",
        ),
    )

    repr_cols = (
        "id",
        "company_id",
        "tenant_id",
        "legal_entity_id",
        "organizational_unit_id",
    )
