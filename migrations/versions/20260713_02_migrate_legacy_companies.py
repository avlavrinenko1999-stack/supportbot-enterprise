"""migrate legacy companies to enterprise structure

Revision ID: 20260713_02
Revises: 20260713_01
Create Date: 2026-07-13
"""

from collections.abc import Mapping
from typing import Any

from alembic import op
import sqlalchemy as sa


revision = "20260713_02"
down_revision = "20260713_01"
branch_labels = None
depends_on = None


DEFAULT_TENANT_CODE = "default"
DEFAULT_TENANT_NAME = "Основной контур"


def _clean(value: Any) -> str | None:
    if value is None:
        return None

    normalized = " ".join(str(value).split())
    return normalized or None


def _row_value(
    row: Mapping[str, Any],
    key: str,
) -> Any:
    return row.get(key)


def upgrade() -> None:
    op.create_table(
        "legacy_company_mappings",
        sa.Column(
            "company_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "legal_entity_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "organizational_unit_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["legal_entity_id"],
            ["legal_entities.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organizational_unit_id"],
            ["organizational_units.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id"),
        sa.UniqueConstraint(
            "organizational_unit_id"
        ),
        sa.UniqueConstraint(
            "company_id",
            "tenant_id",
            name=(
                "uq_legacy_company_mapping_"
                "company_tenant"
            ),
        ),
    )

    op.create_index(
        "ix_legacy_company_mappings_company_id",
        "legacy_company_mappings",
        ["company_id"],
        unique=True,
    )
    op.create_index(
        "ix_legacy_company_mappings_tenant_id",
        "legacy_company_mappings",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_legacy_company_mappings_legal_entity_id",
        "legacy_company_mappings",
        ["legal_entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_legacy_company_mappings_unit_id",
        "legacy_company_mappings",
        ["organizational_unit_id"],
        unique=True,
    )
    op.create_index(
        "ix_legacy_company_mapping_legal_entity",
        "legacy_company_mappings",
        ["legal_entity_id", "company_id"],
        unique=False,
    )

    bind = op.get_bind()
    metadata = sa.MetaData()

    tenants = sa.Table(
        "tenants",
        metadata,
        autoload_with=bind,
    )
    legal_entities = sa.Table(
        "legal_entities",
        metadata,
        autoload_with=bind,
    )
    organizational_units = sa.Table(
        "organizational_units",
        metadata,
        autoload_with=bind,
    )
    companies = sa.Table(
        "companies",
        metadata,
        autoload_with=bind,
    )
    accounts = sa.Table(
        "accounts",
        metadata,
        autoload_with=bind,
    )
    memberships = sa.Table(
        "account_organizational_unit_memberships",
        metadata,
        autoload_with=bind,
    )
    mappings = sa.Table(
        "legacy_company_mappings",
        metadata,
        autoload_with=bind,
    )

    tenant_id = bind.execute(
        sa.select(tenants.c.id).where(
            tenants.c.code == DEFAULT_TENANT_CODE
        )
    ).scalar_one_or_none()

    if tenant_id is None:
        tenant_id = bind.execute(
            tenants.insert()
            .values(
                code=DEFAULT_TENANT_CODE,
                name=DEFAULT_TENANT_NAME,
                is_active=True,
            )
            .returning(tenants.c.id)
        ).scalar_one()

    company_rows = bind.execute(
        sa.select(companies).order_by(companies.c.id)
    ).mappings().all()

    legal_entity_by_inn: dict[str, int] = {}
    legal_entity_by_ogrn: dict[str, int] = {}

    existing_legal_entities = bind.execute(
        sa.select(
            legal_entities.c.id,
            legal_entities.c.inn,
            legal_entities.c.ogrn,
        ).where(
            legal_entities.c.tenant_id == tenant_id
        )
    ).mappings()

    for legal_entity in existing_legal_entities:
        inn = _clean(legal_entity["inn"])
        ogrn = _clean(legal_entity["ogrn"])

        if inn is not None:
            legal_entity_by_inn[inn] = (
                legal_entity["id"]
            )

        if ogrn is not None:
            legal_entity_by_ogrn[ogrn] = (
                legal_entity["id"]
            )

    unit_by_company: dict[int, int] = {}

    for company in company_rows:
        company_id = int(company["id"])

        existing_mapping = bind.execute(
            sa.select(
                mappings.c.organizational_unit_id
            ).where(
                mappings.c.company_id == company_id
            )
        ).scalar_one_or_none()

        if existing_mapping is not None:
            unit_by_company[company_id] = int(
                existing_mapping
            )
            continue

        name = (
            _clean(_row_value(company, "name"))
            or f"Подразделение {company_id}"
        )
        legal_name = _clean(
            _row_value(company, "legal_name")
        )
        inn = _clean(_row_value(company, "inn"))
        kpp = _clean(_row_value(company, "kpp"))
        ogrn = _clean(_row_value(company, "ogrn"))

        legal_entity_id = None

        if inn is not None:
            legal_entity_id = (
                legal_entity_by_inn.get(inn)
            )

        if (
            legal_entity_id is None
            and ogrn is not None
        ):
            legal_entity_id = (
                legal_entity_by_ogrn.get(ogrn)
            )

        if legal_entity_id is None:
            legal_entity_id = bind.execute(
                legal_entities.insert()
                .values(
                    tenant_id=tenant_id,
                    name=name,
                    legal_name=legal_name,
                    inn=inn,
                    kpp=kpp,
                    ogrn=ogrn,
                    legal_address=_clean(
                        _row_value(
                            company,
                            "legal_address",
                        )
                    ),
                    legal_status=_clean(
                        _row_value(
                            company,
                            "legal_status",
                        )
                    ),
                    legal_status_code=_clean(
                        _row_value(
                            company,
                            "legal_status_code",
                        )
                    ),
                    registration_date=_clean(
                        _row_value(
                            company,
                            "registration_date",
                        )
                    ),
                    liquidation_date=_clean(
                        _row_value(
                            company,
                            "liquidation_date",
                        )
                    ),
                    phone=_clean(
                        _row_value(company, "phone")
                    ),
                    last_registry_sync_at=(
                        _row_value(
                            company,
                            "last_registry_sync_at",
                        )
                    ),
                    is_active=bool(
                        _row_value(
                            company,
                            "is_active",
                        )
                    ),
                )
                .returning(legal_entities.c.id)
            ).scalar_one()

            if inn is not None:
                legal_entity_by_inn[inn] = (
                    legal_entity_id
                )

            if ogrn is not None:
                legal_entity_by_ogrn[ogrn] = (
                    legal_entity_id
                )

        organizational_unit_id = bind.execute(
            organizational_units.insert()
            .values(
                tenant_id=tenant_id,
                legal_entity_id=legal_entity_id,
                parent_id=None,
                name=name,
                unit_type="GENERAL",
                code=f"legacy-company-{company_id}",
                is_active=bool(
                    _row_value(company, "is_active")
                ),
            )
            .returning(organizational_units.c.id)
        ).scalar_one()

        bind.execute(
            mappings.insert().values(
                company_id=company_id,
                tenant_id=tenant_id,
                legal_entity_id=legal_entity_id,
                organizational_unit_id=(
                    organizational_unit_id
                ),
            )
        )

        unit_by_company[company_id] = (
            organizational_unit_id
        )

    account_rows = bind.execute(
        sa.select(
            accounts.c.id,
            accounts.c.company_id,
        ).where(
            accounts.c.company_id.is_not(None)
        )
    ).mappings()

    for account in account_rows:
        company_id = int(account["company_id"])
        unit_id = unit_by_company.get(company_id)

        if unit_id is None:
            continue

        membership_exists = bind.execute(
            sa.select(memberships.c.id).where(
                memberships.c.account_id
                == account["id"],
                memberships.c.organizational_unit_id
                == unit_id,
            )
        ).scalar_one_or_none()

        if membership_exists is not None:
            continue

        bind.execute(
            memberships.insert().values(
                account_id=account["id"],
                organizational_unit_id=unit_id,
                position_name=None,
                is_primary=True,
                is_active=True,
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()

    mappings = sa.Table(
        "legacy_company_mappings",
        metadata,
        autoload_with=bind,
    )
    memberships = sa.Table(
        "account_organizational_unit_memberships",
        metadata,
        autoload_with=bind,
    )
    organizational_units = sa.Table(
        "organizational_units",
        metadata,
        autoload_with=bind,
    )
    legal_entities = sa.Table(
        "legal_entities",
        metadata,
        autoload_with=bind,
    )
    tenants = sa.Table(
        "tenants",
        metadata,
        autoload_with=bind,
    )

    mapping_rows = bind.execute(
        sa.select(
            mappings.c.organizational_unit_id,
            mappings.c.legal_entity_id,
            mappings.c.tenant_id,
        )
    ).mappings().all()

    unit_ids = {
        row["organizational_unit_id"]
        for row in mapping_rows
    }
    legal_entity_ids = {
        row["legal_entity_id"]
        for row in mapping_rows
    }
    tenant_ids = {
        row["tenant_id"]
        for row in mapping_rows
    }

    if unit_ids:
        bind.execute(
            memberships.delete().where(
                memberships.c.organizational_unit_id.in_(
                    unit_ids
                )
            )
        )

    bind.execute(mappings.delete())

    if unit_ids:
        bind.execute(
            organizational_units.delete().where(
                organizational_units.c.id.in_(
                    unit_ids
                )
            )
        )

    if legal_entity_ids:
        remaining_units = sa.select(
            organizational_units.c.legal_entity_id
        )

        bind.execute(
            legal_entities.delete().where(
                legal_entities.c.id.in_(
                    legal_entity_ids
                ),
                legal_entities.c.id.not_in(
                    remaining_units
                ),
            )
        )

    for tenant_id in tenant_ids:
        has_entities = bind.execute(
            sa.select(
                sa.func.count(legal_entities.c.id)
            ).where(
                legal_entities.c.tenant_id
                == tenant_id
            )
        ).scalar_one()

        has_units = bind.execute(
            sa.select(
                sa.func.count(
                    organizational_units.c.id
                )
            ).where(
                organizational_units.c.tenant_id
                == tenant_id
            )
        ).scalar_one()

        tenant_code = bind.execute(
            sa.select(tenants.c.code).where(
                tenants.c.id == tenant_id
            )
        ).scalar_one_or_none()

        if (
            tenant_code == DEFAULT_TENANT_CODE
            and has_entities == 0
            and has_units == 0
        ):
            bind.execute(
                tenants.delete().where(
                    tenants.c.id == tenant_id
                )
            )

    op.drop_index(
        "ix_legacy_company_mapping_legal_entity",
        table_name="legacy_company_mappings",
    )
    op.drop_index(
        "ix_legacy_company_mappings_unit_id",
        table_name="legacy_company_mappings",
    )
    op.drop_index(
        "ix_legacy_company_mappings_legal_entity_id",
        table_name="legacy_company_mappings",
    )
    op.drop_index(
        "ix_legacy_company_mappings_tenant_id",
        table_name="legacy_company_mappings",
    )
    op.drop_index(
        "ix_legacy_company_mappings_company_id",
        table_name="legacy_company_mappings",
    )

    op.drop_table("legacy_company_mappings")
