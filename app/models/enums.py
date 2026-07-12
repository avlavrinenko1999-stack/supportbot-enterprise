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
