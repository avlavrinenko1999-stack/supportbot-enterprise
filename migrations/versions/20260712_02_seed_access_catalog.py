"""seed access catalog

Revision ID: 20260712_02
Revises: 20260712_01
Create Date: 2026-07-12
"""

from alembic import op
import sqlalchemy as sa


revision = "20260712_02"
down_revision = "20260712_01"
branch_labels = None
depends_on = None


ROLES = {
    "platform_admin": (
        "Администратор платформы",
        "Полный системный доступ ко всей платформе.",
    ),
    "holding_admin": (
        "Администратор холдинга",
        "Управление компаниями и доступами своего холдинга.",
    ),
    "company_admin": (
        "Администратор компании",
        "Управление одной компанией и её сотрудниками.",
    ),
    "support_manager": (
        "Руководитель поддержки",
        "Управление поддержкой, очередями, SLA и исполнителями.",
    ),
    "coordinator": (
        "Координатор",
        "Распределение, контроль и эскалация обращений.",
    ),
    "operator": (
        "Оператор",
        "Обработка назначенных обращений.",
    ),
    "observer": (
        "Наблюдатель",
        "Просмотр доступных обращений без изменения данных.",
    ),
    "user": (
        "Пользователь",
        "Создание и ведение собственных обращений.",
    ),
    "auditor": (
        "Аудитор",
        "Доступ только для чтения и контроля аудита.",
    ),
}


PERMISSIONS = {
    "platform.read": ("Просмотр платформы", True),
    "platform.manage": ("Управление платформой", True),
    "organization.read": ("Просмотр организаций", True),
    "organization.manage": ("Управление организациями", True),
    "holding.read": ("Просмотр холдинга", True),
    "holding.manage": ("Управление холдингом", True),
    "holding.policy.manage": (
        "Управление политиками холдинга",
        True,
    ),
    "company.read": ("Просмотр компании", True),
    "company.update": ("Изменение компании", False),
    "company.disable": ("Отключение компании", False),
    "company.settings.manage": (
        "Управление настройками компании",
        False,
    ),
    "employee.read": ("Просмотр сотрудников", True),
    "employee.invite": (
        "Создание приглашений сотрудникам",
        False,
    ),
    "employee.update": ("Изменение сотрудников", False),
    "employee.disable": ("Отключение сотрудников", False),
    "employee.role.assign": (
        "Назначение ролей сотрудникам",
        False,
    ),
    "ticket.create": ("Создание обращений", False),
    "ticket.read.own": (
        "Просмотр собственных обращений",
        False,
    ),
    "ticket.read.company": (
        "Просмотр обращений компании",
        True,
    ),
    "ticket.read.queue": (
        "Просмотр обращений очереди",
        True,
    ),
    "ticket.read.all": ("Просмотр всех обращений", True),
    "ticket.assign": ("Назначение исполнителя", False),
    "ticket.reply": ("Ответ в обращении", False),
    "ticket.status.change": (
        "Изменение статуса обращения",
        False,
    ),
    "ticket.priority.change": (
        "Изменение приоритета обращения",
        False,
    ),
    "ticket.escalate": ("Эскалация обращения", False),
    "ticket.close": ("Закрытие обращения", False),
    "category.read": ("Просмотр категорий", True),
    "category.manage": ("Управление категориями", False),
    "queue.read": ("Просмотр очередей поддержки", True),
    "queue.manage": (
        "Управление очередями поддержки",
        False,
    ),
    "queue.member.manage": (
        "Управление участниками очередей",
        False,
    ),
    "sla.read": ("Просмотр SLA", True),
    "sla.manage": ("Управление SLA", False),
    "report.read.company": (
        "Просмотр отчётов компании",
        True,
    ),
    "report.read.holding": (
        "Просмотр отчётов холдинга",
        True,
    ),
    "report.read.platform": (
        "Просмотр отчётов платформы",
        True,
    ),
    "audit.read.company": (
        "Просмотр аудита компании",
        True,
    ),
    "audit.read.holding": (
        "Просмотр аудита холдинга",
        True,
    ),
    "audit.read.organization": (
        "Просмотр аудита организации",
        True,
    ),
    "audit.read.platform": (
        "Просмотр аудита платформы",
        True,
    ),
    "support_contract.read": (
        "Просмотр договоров поддержки",
        True,
    ),
    "support_contract.manage": (
        "Управление договорами поддержки",
        False,
    ),
}


ROLE_PERMISSIONS = {
    "platform_admin": set(PERMISSIONS),
    "holding_admin": {
        "holding.read",
        "holding.manage",
        "holding.policy.manage",
        "company.read",
        "company.update",
        "company.settings.manage",
        "employee.read",
        "employee.invite",
        "employee.update",
        "employee.disable",
        "employee.role.assign",
        "ticket.read.company",
        "ticket.assign",
        "ticket.reply",
        "ticket.status.change",
        "ticket.priority.change",
        "ticket.escalate",
        "ticket.close",
        "category.read",
        "category.manage",
        "queue.read",
        "queue.manage",
        "queue.member.manage",
        "sla.read",
        "sla.manage",
        "report.read.company",
        "report.read.holding",
        "audit.read.company",
        "audit.read.holding",
    },
    "company_admin": {
        "company.read",
        "company.update",
        "company.settings.manage",
        "employee.read",
        "employee.invite",
        "employee.update",
        "employee.disable",
        "employee.role.assign",
        "ticket.read.company",
        "ticket.assign",
        "ticket.reply",
        "ticket.status.change",
        "ticket.priority.change",
        "ticket.escalate",
        "ticket.close",
        "category.read",
        "category.manage",
        "queue.read",
        "queue.manage",
        "queue.member.manage",
        "sla.read",
        "sla.manage",
        "report.read.company",
        "audit.read.company",
    },
    "support_manager": {
        "company.read",
        "employee.read",
        "ticket.read.company",
        "ticket.read.queue",
        "ticket.assign",
        "ticket.reply",
        "ticket.status.change",
        "ticket.priority.change",
        "ticket.escalate",
        "ticket.close",
        "category.read",
        "queue.read",
        "queue.manage",
        "queue.member.manage",
        "sla.read",
        "sla.manage",
        "report.read.company",
        "audit.read.company",
    },
    "coordinator": {
        "company.read",
        "employee.read",
        "ticket.read.company",
        "ticket.read.queue",
        "ticket.assign",
        "ticket.reply",
        "ticket.status.change",
        "ticket.priority.change",
        "ticket.escalate",
        "ticket.close",
        "category.read",
        "queue.read",
        "sla.read",
    },
    "operator": {
        "company.read",
        "ticket.read.queue",
        "ticket.reply",
        "ticket.status.change",
        "ticket.escalate",
        "category.read",
        "queue.read",
        "sla.read",
    },
    "observer": {
        "company.read",
        "employee.read",
        "ticket.read.company",
        "ticket.read.queue",
        "category.read",
        "queue.read",
        "sla.read",
        "report.read.company",
    },
    "user": {
        "company.read",
        "ticket.create",
        "ticket.read.own",
        "ticket.reply",
        "category.read",
    },
    "auditor": {
        "company.read",
        "employee.read",
        "ticket.read.company",
        "category.read",
        "queue.read",
        "sla.read",
        "report.read.company",
        "audit.read.company",
    },
}


def upgrade() -> None:
    bind = op.get_bind()

    role_insert = sa.text(
        """
        INSERT INTO roles (
            code,
            name,
            description,
            is_system,
            is_active,
            created_at,
            updated_at
        )
        VALUES (
            :code,
            :name,
            :description,
            true,
            true,
            now(),
            now()
        )
        ON CONFLICT (code) DO NOTHING
        """
    )

    for code, (name, description) in ROLES.items():
        bind.execute(
            role_insert,
            {
                "code": code,
                "name": name,
                "description": description,
            },
        )

    permission_insert = sa.text(
        """
        INSERT INTO permissions (
            code,
            name,
            description,
            inherits_downward,
            is_active,
            created_at,
            updated_at
        )
        VALUES (
            :code,
            :name,
            NULL,
            :inherits_downward,
            true,
            now(),
            now()
        )
        ON CONFLICT (code) DO NOTHING
        """
    )

    for code, (name, inherits_downward) in PERMISSIONS.items():
        bind.execute(
            permission_insert,
            {
                "code": code,
                "name": name,
                "inherits_downward": inherits_downward,
            },
        )

    link_insert = sa.text(
        """
        INSERT INTO role_permissions (
            role_id,
            permission_id,
            created_at,
            updated_at
        )
        SELECT
            roles.id,
            permissions.id,
            now(),
            now()
        FROM roles
        CROSS JOIN permissions
        WHERE roles.code = :role_code
          AND permissions.code = :permission_code
          AND NOT EXISTS (
              SELECT 1
              FROM role_permissions
              WHERE role_permissions.role_id = roles.id
                AND role_permissions.permission_id = permissions.id
          )
        """
    )

    for role_code, permission_codes in ROLE_PERMISSIONS.items():
        for permission_code in permission_codes:
            bind.execute(
                link_insert,
                {
                    "role_code": role_code,
                    "permission_code": permission_code,
                },
            )


def downgrade() -> None:
    bind = op.get_bind()

    role_codes = tuple(ROLES)
    permission_codes = tuple(PERMISSIONS)

    bind.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE role_id IN (
                SELECT id
                FROM roles
                WHERE code = ANY(:role_codes)
            )
            AND permission_id IN (
                SELECT id
                FROM permissions
                WHERE code = ANY(:permission_codes)
            )
            """
        ),
        {
            "role_codes": list(role_codes),
            "permission_codes": list(permission_codes),
        },
    )

    bind.execute(
        sa.text(
            """
            DELETE FROM roles
            WHERE code = ANY(:role_codes)
              AND is_system = true
            """
        ),
        {"role_codes": list(role_codes)},
    )

    bind.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE code = ANY(:permission_codes)
              AND NOT EXISTS (
                  SELECT 1
                  FROM role_permissions
                  WHERE role_permissions.permission_id = permissions.id
              )
            """
        ),
        {"permission_codes": list(permission_codes)},
    )
