SYSTEM_ROLES: dict[str, dict[str, str]] = {
    "platform_admin": {
        "name": "Администратор платформы",
        "description": "Полный системный доступ ко всей платформе.",
    },
    "holding_admin": {
        "name": "Администратор холдинга",
        "description": "Управление подразделениеми и доступами своего холдинга.",
    },
    "business_unit_admin": {
        "name": "Администратор подразделения",
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
    "business_unit.read": {
        "name": "Просмотр подразделения",
        "inherits_downward": True,
    },
    "business_unit.update": {
        "name": "Изменение подразделения",
        "inherits_downward": False,
    },
    "business_unit.disable": {
        "name": "Отключение подразделения",
        "inherits_downward": False,
    },
    "business_unit.settings.manage": {
        "name": "Управление настройками подразделения",
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
    "ticket.read.business_unit": {
        "name": "Просмотр обращений подразделения",
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
    "report.read.business_unit": {
        "name": "Просмотр отчётов подразделения",
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
    "audit.read.business_unit": {
        "name": "Просмотр аудита подразделения",
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
            "business_unit.read",
            "business_unit.update",
            "business_unit.settings.manage",
            "employee.read",
            "employee.invite",
            "employee.update",
            "employee.disable",
            "employee.role.assign",
            "ticket.read.business_unit",
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
            "report.read.business_unit",
            "report.read.holding",
            "audit.read.business_unit",
            "audit.read.holding",
        }
    ),
    "business_unit_admin": frozenset(
        {
            "business_unit.read",
            "business_unit.update",
            "business_unit.settings.manage",
            "employee.read",
            "employee.invite",
            "employee.update",
            "employee.disable",
            "employee.role.assign",
            "ticket.read.business_unit",
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
            "report.read.business_unit",
            "audit.read.business_unit",
        }
    ),
    "support_manager": frozenset(
        {
            "business_unit.read",
            "employee.read",
            "ticket.read.business_unit",
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
            "report.read.business_unit",
            "audit.read.business_unit",
        }
    ),
    "coordinator": frozenset(
        {
            "business_unit.read",
            "employee.read",
            "ticket.read.business_unit",
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
            "business_unit.read",
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
            "business_unit.read",
            "employee.read",
            "ticket.read.business_unit",
            "ticket.read.queue",
            "category.read",
            "queue.read",
            "sla.read",
            "report.read.business_unit",
        }
    ),
    "user": frozenset(
        {
            "business_unit.read",
            "ticket.create",
            "ticket.read.own",
            "ticket.reply",
            "category.read",
        }
    ),
    "auditor": frozenset(
        {
            "business_unit.read",
            "employee.read",
            "ticket.read.business_unit",
            "category.read",
            "queue.read",
            "sla.read",
            "report.read.business_unit",
            "audit.read.business_unit",
        }
    ),
}
