from enum import Enum


class UserRole(str, Enum):
    """Роли пользователей."""

    ADMIN = "admin"
    COORDINATOR = "coordinator"
    OPERATOR = "operator"
    OBSERVER = "observer"
    USER = "user"


class TicketStatus(str, Enum):
    """Статусы обращения."""

    NEW = "new"

    IN_PROGRESS = "in_progress"

    WAITING_USER = "waiting_user"

    WAITING_OPERATOR = "waiting_operator"

    RESOLVED = "resolved"

    CLOSED = "closed"


class InviteRole(str, Enum):
    """Кого приглашает ссылка."""

    COORDINATOR = "coordinator"

    OPERATOR = "operator"

    OBSERVER = "observer"

    USER = "user"


class EventType(str, Enum):
    """Тип события истории обращения."""

    CREATED = "created"

    STATUS_CHANGED = "status_changed"

    MESSAGE = "message"

    INTERNAL_NOTE = "internal_note"

    ATTACHMENT = "attachment"

    ASSIGNED = "assigned"

    CLOSED = "closed"

    REOPENED = "reopened"


class OrganizationType(str, Enum):
    """Тип организации в организационной структуре."""

    PLATFORM = "platform"
    CUSTOMER = "customer"
    SUPPORT_PROVIDER = "support_provider"
    PARTNER = "partner"


class OrganizationalUnitType(str, Enum):
    """Тип элемента рабочей организационной структуры."""

    GENERAL = "general"
    BUSINESS_UNIT = "business_unit"
    DIVISION = "division"
    DEPARTMENT = "department"
    BRANCH = "branch"
    OFFICE = "office"
    PLANT = "plant"
    WAREHOUSE = "warehouse"
    SERVICE_CENTER = "service_center"
    COST_CENTER = "cost_center"
    REGION = "region"
    PROJECT_OFFICE = "project_office"


class ScopeType(str, Enum):
    """Область действия роли или разрешения."""

    PLATFORM = "platform"
    ORGANIZATION = "organization"
    HOLDING = "holding"
    COMPANY = "company"
    SUPPORT_CONTRACT = "support_contract"
    SUPPORT_QUEUE = "support_queue"
    TICKET = "ticket"
