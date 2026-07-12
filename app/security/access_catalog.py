SYSTEM_ROLES: dict[str, dict[str, str]] = {
    "platform_admin": {
        "name": "Администратор платформы",
        "description": "Полный системный доступ ко всей платформе.",
    },
    "holding_admin": {
        "name": "Администратор холдинга",
        "description": "Управление компаниями и доступами своего холдинга.",
    },
    "company_admin": {
        "name": "Администратор компании",
        "description": "Управление одной компанией и её сотрудниками.",
    },
    "support_manager": {
        "name": "Руководитель поддержки",
        "description": "Управление поддержкой, очередями, SLA и исполнителями.",
    },
    "coordinator": {
        "name": "Координатор",
        "description": "Распределение, контроль и эскалация обращений.",
    },
    "operator": {
        "name": "Оператор",
        "description": "Обработка назначенных обращений.",
    },
    "observer": {
        "name": "Наблюдатель",
        "description": "Просмотр доступных обращений без изменения данных.",
    },
    "user": {
        "name": "Пользователь",
        "description": "Создание и ведение собственных обращений.",
    },
    "auditor": {
        "name": "Аудитор",
        "description": "Доступ только для чтения и контроля аудита.",
    },
}


PERMISSIONS: dict[str, dict[str, object]] = {
    "platform.read": {
        "name": "Просмотр платформы",
        "inherits_downward": True,
    },
    "platform.manage": {
        "name": "Управление платформой",
        "inherits_downward": True,
    },
    "organization.read": {
        "name": "Просмотр организаций",
        "inherits_downward": True,
    },
    "organization.manage": {
        "name": "Управление организациями",
        "inherits_downward": True,
    },
    "holding.read": {
        "name": "Просмотр холдинга",
        "inherits_downward": True,
    },
    "holding.manage": {
        "name": "Управление холдингом",
        "inherits_downward": True,
    },
    "holding.policy.manage": {
        "name": "Управление политиками холдинга",
        "inherits_downward": True,
    },
    "company.read": {
        "name": "Просмотр компании",
        "inherits_downward": True,
    },
    "company.update": {
        "name": "Изменение компании",
        "inherits_downward": False,
    },
    "company.disable": {
        "name": "Отключение компании",
        "inherits_downward": False,
    },
    "company.settings.manage": {
        "name": "Управление настройками компании",
        "inherits_downward": False,
    },
    "employee.read": {
        "name": "Просмотр сотрудников",
        "inherits_downward": True,
    },
    "employee.invite": {
        "name": "Создание приглашений сотрудникам",
        "inherits_downward": False,
    },
    "employee.update": {
        "name": "Изменение сотрудников",
        "inherits_downward": False,
    },
    "employee.disable": {
        "name": "Отключение сотрудников",
        "inherits_downward": False,
    },
    "employee.role.assign": {
        "name": "Назначение ролей сотрудникам",
        "inherits_downward": False,
    },
    "ticket.create": {
        "name": "Создание обращений",
        "inherits_downward": False,
    },
    "ticket.read.own": {
        "name": "Просмотр собственных обращений",
        "inherits_downward": False,
    },
    "ticket.read.company": {
        "name": "Просмотр обращений компании",
        "inherits_downward": True,
    },
    "ticket.read.queue": {
        "name": "Просмотр обращений очереди",
        "inherits_downward": True,
    },
    "ticket.read.all": {
        "name": "Просмотр всех обращений",
        "inherits_downward": True,
    },
    "ticket.assign": {
        "name": "Назначение исполнителя",
        "inherits_downward": False,
    },
    "ticket.reply": {
        "name": "Ответ в обращении",
        "inherits_downward": False,
    },
    "ticket.status.change": {
        "name": "Изменение статуса обращения",
        "inherits_downward": False,
    },
    "ticket.priority.change": {
        "name": "Изменение приоритета обращения",
        "inherits_downward": False,
    },
    "ticket.escalate": {
        "name": "Эскалация обращения",
        "inherits_downward": False,
    },
    "ticket.close": {
        "name": "Закрытие обращения",
        "inherits_downward": False,
    },
    "category.read": {
        "name": "Просмотр категорий",
        "inherits_downward": True,
    },
    "category.manage": {
        "name": "Управление категориями",
        "inherits_downward": False,
    },
    "queue.read": {
        "name": "Просмотр очередей поддержки",
        "inherits_downward": True,
    },
    "queue.manage": {
        "name": "Управление очередями поддержки",
        "inherits_downward": False,
    },
    "queue.member.manage": {
        "name": "Управление участниками очередей",
        "inherits_downward": False,
    },
    "sla.read": {
        "name": "Просмотр SLA",
        "inherits_downward": True,
    },
    "sla.manage": {
        "name": "Управление SLA",
        "inherits_downward": False,
    },
    "report.read.company": {
        "name": "Просмотр отчётов компании",
        "inherits_downward": True,
    },
    "report.read.holding": {
        "name": "Просмотр отчётов холдинга",
        "inherits_downward": True,
    },
    "report.read.platform": {
        "name": "Просмотр отчётов платформы",
        "inherits_downward": True,
    },
    "audit.read.company": {
        "name": "Просмотр аудита компании",
        "inherits_downward": True,
    },
    "audit.read.holding": {
        "name": "Просмотр аудита холдинга",
        "inherits_downward": True,
    },
    "audit.read.organization": {
        "name": "Просмотр аудита организации",
        "inherits_downward": True,
    },
    "audit.read.platform": {
        "name": "Просмотр аудита платформы",
        "inherits_downward": True,
    },
    "support_contract.read": {
        "name": "Просмотр договоров поддержки",
        "inherits_downward": True,
    },
    "support_contract.manage": {
        "name": "Управление договорами поддержки",
        "inherits_downward": False,
    },
}


ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "platform_admin": frozenset(PERMISSIONS),
    "holding_admin": frozenset(
        {
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
        }
    ),
    "company_admin": frozenset(
        {
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
        }
    ),
    "support_manager": frozenset(
        {
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
        }
    ),
    "coordinator": frozenset(
        {
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
        }
    ),
    "operator": frozenset(
        {
            "company.read",
            "ticket.read.queue",
            "ticket.reply",
            "ticket.status.change",
            "ticket.escalate",
            "category.read",
            "queue.read",
            "sla.read",
        }
    ),
    "observer": frozenset(
        {
            "company.read",
            "employee.read",
            "ticket.read.company",
            "ticket.read.queue",
            "category.read",
            "queue.read",
            "sla.read",
            "report.read.company",
        }
    ),
    "user": frozenset(
        {
            "company.read",
            "ticket.create",
            "ticket.read.own",
            "ticket.reply",
            "category.read",
        }
    ),
    "auditor": frozenset(
        {
            "company.read",
            "employee.read",
            "ticket.read.company",
            "category.read",
            "queue.read",
            "sla.read",
            "report.read.company",
            "audit.read.company",
        }
    ),
}
