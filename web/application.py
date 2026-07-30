import asyncio
import hashlib
import hmac
import html
import json
import logging
from io import BytesIO
import os
import re
import secrets
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import aiohttp
import qrcode
from aiohttp import web
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database.db import AsyncSessionLocal
from app.models.account import Account
from app.models.access_audit_event import AccessAuditEvent
from app.models.email_change_request import EmailChangeRequest
from app.models.account_organizational_unit_membership import (
    AccountOrganizationalUnitMembership,
)
from app.models.holding import Holding
from app.models.enums import (
    InviteRole,
    OrganizationType,
    ScopeType,
    TicketStatus,
    UserRole,
)
from app.models.invite import Invite
from app.models.mail_settings import MailSettings
from app.models.message import Message
from app.models.organization import Organization
from app.models.organizational_unit import OrganizationalUnit
from app.models.role_assignment import RoleAssignment
from app.models.role import Role
from app.models.ticket import Ticket
from app.models.two_factor_setting import TwoFactorSetting
from app.security.authorization import AuthorizationService
from app.security.access_audit_access import AccessAuditAccessService
from app.security.access_scope import AccessScope
from app.security.business_unit_access import BusinessUnitAccessService
from app.security.holding_access import HoldingAccessService
from app.security.organization_access import OrganizationAccessService
from app.security.permissions import Permission
from app.security.permissions import role_permissions
from app.security.localization import get_permission_name, get_role_name
from app.security.role_grant_policy import ROLE_LABELS, RoleGrantPolicy
from app.services.employee_service import EmployeeService
from app.services.company_structure_pdf_service import CompanyStructurePdfService
from app.services.holding_audit_service import HoldingAuditService
from app.services.holding_service import HoldingService
from app.services.invite_service import InviteService
from app.services.language_pack_service import LanguagePackService
from app.services.guest_language_service import GuestLanguageService
from app.services.language_cleanup_service import LanguageCleanupService
from app.repositories.language_repository import LanguageRepository
from app.services.role_assignment_service import RoleAssignmentService
from app.services.web_identity_service import WebIdentityService
from app.services.password_recovery_service import PasswordRecoveryService
from app.services.two_factor_service import TwoFactorService
from app.services.organization_audit_service import OrganizationAuditService
from app.services.organization_registry_service import OrganizationRegistryService
from app.services.organization_service import OrganizationService
from app.keyboards.organization import organization_type_label


logger = logging.getLogger(__name__)


STATIC_ROOT = Path(__file__).resolve().parent / "static"
SESSION_COOKIE = "supportbot_session"
EMBEDDED_COOKIE = "supportbot_embedded"
GUEST_LANGUAGE_COOKIE = "supportbot_guest_language"
LOGIN_TTL = timedelta(minutes=10)
SESSION_TTL = timedelta(hours=12)
WEB_PUBLIC_URL = os.getenv("WEB_PUBLIC_URL", "http://127.0.0.1:8080").rstrip("/")
APP_BUILD = "20260722-88"
WEB_SESSIONS_FILE = Path(__file__).resolve().parents[1] / "data" / "web_sessions.json"
LOGIN_TIMES_FILE = Path(__file__).resolve().parents[1] / "data" / "web_login_times.json"
WORK_TRACKING_FILE = Path(__file__).resolve().parents[1] / "data" / "work_tracking.json"
PRESENCE_ONLINE_TTL = timedelta(seconds=75)
PRESENCE_ACTIVE_TTL = timedelta(seconds=90)
DISPLAY_TIMEZONE = ZoneInfo("Europe/Kaliningrad")
WORK_STATE_LABELS = {
    "not_started": "Рабочий день не начат",
    "working": "Работает",
    "lunch": "На обеде",
    "break": "На перерыве",
    "meeting": "На совещании",
    "other": "Отсутствует по прочей причине",
    "vacation": "В отпуске",
    "sick_leave": "На больничном",
    "business_trip": "В командировке",
    "day_off": "На отгуле",
    "finished": "Рабочий день завершён",
}
OFFICIAL_WORK_STATES = {"vacation", "sick_leave", "business_trip", "day_off"}


@dataclass(slots=True)
class LoginChallenge:
    account_id: int
    code_hash: str
    expires_at: datetime
    attempts: int = 0


@dataclass(slots=True)
class WebSession:
    account_id: int
    csrf_token: str
    expires_at: datetime
    login_at: datetime
    last_seen_at: datetime
    last_activity_at: datetime


@dataclass(slots=True)
class TwoFactorChallenge:
    account_id: int
    expires_at: datetime
    embedded: bool = False
    attempts: int = 0
    recovery_codes: list[str] | None = None


@dataclass(slots=True)
class AdminTwoFactorRecoveryChallenge:
    account_id: int
    code_hash: str
    expires_at: datetime
    attempts: int = 0


@dataclass(slots=True)
class OneCExchangeTicket:
    account_id: int
    expires_at: datetime


@dataclass(slots=True)
class LanguageInstallJob:
    account_id: int
    query: str
    language_code: str
    language_name: str
    progress: int
    message: str
    status: str
    created_at: datetime
    error: str | None = None


@dataclass(slots=True)
class GuestLanguageSession:
    csrf_token: str
    language_code: str
    expires_at: datetime


@dataclass(slots=True)
class GuestLanguageJob:
    guest_id: str
    query: str
    language_code: str
    language_name: str
    flag: str
    progress: int
    message: str
    complete_message: str
    failure_message: str
    package_preexisting: bool
    web_translation_preexisting: bool
    last_seen_at: datetime
    heartbeat_count: int
    status: str
    created_at: datetime
    error: str | None = None


LOGIN_CHALLENGES: dict[str, LoginChallenge] = {}
WEB_SESSIONS: dict[str, WebSession] = {}
LAST_LOGIN_TIMES: dict[int, datetime] = {}
WORK_TRACKING: dict[str, dict] = {"accounts": {}, "workdays": {}}
TWO_FACTOR_CHALLENGES: dict[str, TwoFactorChallenge] = {}
ADMIN_2FA_RECOVERY_CHALLENGES: dict[str, AdminTwoFactorRecoveryChallenge] = {}
ADMIN_2FA_RECOVERY_LAST_SENT: dict[int, datetime] = {}
ONE_C_EXCHANGE_TICKETS: dict[str, OneCExchangeTicket] = {}
LANGUAGE_INSTALL_JOBS: dict[str, LanguageInstallJob] = {}
LANGUAGE_INSTALL_TASKS: set[asyncio.Task] = set()
GUEST_LANGUAGE_SESSIONS: dict[str, GuestLanguageSession] = {}
GUEST_LANGUAGE_JOBS: dict[str, GuestLanguageJob] = {}
GUEST_LANGUAGE_TASKS: set[asyncio.Task] = set()

EMAIL_CHANGE_TTL = timedelta(minutes=15)
EMAIL_CHANGE_RESEND = timedelta(seconds=60)
EMAIL_CHANGE_MAX_ATTEMPTS = 6


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def now() -> datetime:
    return datetime.now(timezone.utc)


def save_web_sessions() -> None:
    WEB_SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        token: {
            "account_id": session.account_id,
            "csrf_token": session.csrf_token,
            "expires_at": session.expires_at.isoformat(),
            "login_at": session.login_at.isoformat(),
            "last_seen_at": session.last_seen_at.isoformat(),
            "last_activity_at": session.last_activity_at.isoformat(),
        }
        for token, session in WEB_SESSIONS.items()
        if session.expires_at > now()
    }
    temporary = WEB_SESSIONS_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload), encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, WEB_SESSIONS_FILE)


def save_login_times() -> None:
    LOGIN_TIMES_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = LOGIN_TIMES_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps({str(account_id): value.isoformat() for account_id, value in LAST_LOGIN_TIMES.items()}),
        encoding="utf-8",
    )
    os.chmod(temporary, 0o600)
    os.replace(temporary, LOGIN_TIMES_FILE)


def load_web_sessions() -> None:
    try:
        payload = json.loads(WEB_SESSIONS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return
    for token, item in payload.items():
        try:
            fallback_login = datetime.fromisoformat(str(item["expires_at"])) - SESSION_TTL
            session = WebSession(
                account_id=int(item["account_id"]),
                csrf_token=str(item["csrf_token"]),
                expires_at=datetime.fromisoformat(str(item["expires_at"])),
                login_at=datetime.fromisoformat(str(item.get("login_at") or fallback_login.isoformat())),
                last_seen_at=datetime.fromisoformat(str(item.get("last_seen_at") or fallback_login.isoformat())),
                last_activity_at=datetime.fromisoformat(str(item.get("last_activity_at") or fallback_login.isoformat())),
            )
        except (KeyError, TypeError, ValueError):
            continue
        if session.expires_at > now():
            WEB_SESSIONS[str(token)] = session


load_web_sessions()

try:
    LAST_LOGIN_TIMES.update({
        int(account_id): datetime.fromisoformat(value)
        for account_id, value in json.loads(LOGIN_TIMES_FILE.read_text(encoding="utf-8")).items()
    })
except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError, ValueError):
    pass

try:
    loaded_tracking = json.loads(WORK_TRACKING_FILE.read_text(encoding="utf-8"))
    if isinstance(loaded_tracking, dict):
        WORK_TRACKING.update(loaded_tracking)
except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError):
    pass


def save_work_tracking() -> None:
    WORK_TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = WORK_TRACKING_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(WORK_TRACKING), encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, WORK_TRACKING_FILE)


def tracking_account(account_id: int) -> dict:
    accounts = WORK_TRACKING.setdefault("accounts", {})
    created = str(account_id) not in accounts
    item = accounts.setdefault(str(account_id), {"enabled": True, "token": secrets.token_urlsafe(32)})
    if not item.get("token"):
        item["token"] = secrets.token_urlsafe(32)
        created = True
    if created:
        save_work_tracking()
    return item


def record_workday_start(account_id: int, logged_in_at: datetime) -> None:
    local = logged_in_at.astimezone(DISPLAY_TIMEZONE)
    key = f"{account_id}:{local.date().isoformat()}"
    workdays = WORK_TRACKING.setdefault("workdays", {})
    if key not in workdays:
        workdays[key] = logged_in_at.isoformat()
        account = tracking_account(account_id)
        account.update({"work_state": "not_started", "work_state_date": local.date().isoformat(), "work_state_changed_at": logged_in_at.isoformat()})
        WORK_TRACKING.setdefault("events", {}).setdefault(key, []).append({"state": "not_started", "at": logged_in_at.isoformat(), "source": "login"})
        save_work_tracking()


def parse_official_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError as error:
        raise ValueError("Укажите корректные дату и время.") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=DISPLAY_TIMEZONE)
    return parsed.astimezone(timezone.utc)


def active_official_absence(account_id: int, timestamp: datetime) -> dict | None:
    for absence in reversed(tracking_account(account_id).get("official_absences", [])):
        try:
            starts_at = datetime.fromisoformat(str(absence["starts_at"]))
            ends_at = datetime.fromisoformat(str(absence["ends_at"]))
        except (KeyError, ValueError, TypeError):
            continue
        if starts_at <= timestamp < ends_at:
            return absence
    return None


def set_work_state(account_id: int, state: str, source: str, *, timestamp: datetime | None = None, reason: str = "", starts_at: str = "", ends_at: str = "") -> dict:
    if state not in WORK_STATE_LABELS:
        raise ValueError("Неизвестное рабочее состояние.")
    timestamp = timestamp or now()
    local_date = timestamp.astimezone(DISPLAY_TIMEZONE).date().isoformat()
    account = tracking_account(account_id)
    current_absence = active_official_absence(account_id, timestamp)
    # TODO(task-system): досрочный выход из официального отсутствия должен создавать
    # задачу руководителю и применяться только после его подтверждения.
    if state == "working" and current_absence is not None:
        raise ValueError("Официальное отсутствие ещё действует. Досрочный возврат к работе должен подтвердить руководитель.")
    if state in OFFICIAL_WORK_STATES:
        start = parse_official_datetime(starts_at)
        end = parse_official_datetime(ends_at)
        if start < timestamp - timedelta(seconds=60):
            raise ValueError("Дата начала официального отсутствия не может быть раньше текущих даты и времени.")
        if end <= start:
            raise ValueError("Дата окончания должна быть позже даты начала.")
        for existing in account.get("official_absences", []):
            try:
                existing_start = datetime.fromisoformat(str(existing["starts_at"]))
                existing_end = datetime.fromisoformat(str(existing["ends_at"]))
            except (KeyError, ValueError, TypeError):
                continue
            if start < existing_end and end > existing_start:
                raise ValueError("Указанный период пересекается с другим официальным отсутствием.")
        absence = {"state": state, "starts_at": start.isoformat(), "ends_at": end.isoformat(), "created_at": timestamp.isoformat(), "source": source}
        account.setdefault("official_absences", []).append(absence)
        save_work_tracking()
        return {"state": state if start <= timestamp else account.get("work_state", "not_started"), "label": WORK_STATE_LABELS[state], "starts_at": start.isoformat(), "ends_at": end.isoformat(), "scheduled": start > timestamp}
    reason = " ".join(str(reason).split())[:500]
    account.update({"work_state": state, "work_state_date": local_date, "work_state_changed_at": timestamp.isoformat()})
    if state == "other":
        account["work_state_reason"] = reason
    else:
        account.pop("work_state_reason", None)
    key = f"{account_id}:{local_date}"
    event = {"state": state, "at": timestamp.isoformat(), "source": source}
    if reason:
        event["reason"] = reason
    WORK_TRACKING.setdefault("events", {}).setdefault(key, []).append(event)
    save_work_tracking()
    return {"state": state, "label": WORK_STATE_LABELS[state], "changed_at": timestamp.isoformat()}


def schedule_for(account_id: int) -> dict | None:
    value = tracking_account(account_id).get("schedule")
    if not isinstance(value, dict) or not value.get("start") or not value.get("end"):
        return None
    return value


def schedule_bounds(account_id: int, timestamp: datetime) -> tuple[datetime, datetime] | None:
    schedule = schedule_for(account_id)
    local = timestamp.astimezone(DISPLAY_TIMEZONE)
    if schedule is None or local.weekday() not in schedule.get("weekdays", []):
        return None
    try:
        start_hour, start_minute = map(int, schedule["start"].split(":"))
        end_hour, end_minute = map(int, schedule["end"].split(":"))
    except (ValueError, AttributeError):
        return None
    start = local.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
    end = local.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
    if end <= start:
        end += timedelta(days=1)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def workday_events(account_id: int, timestamp: datetime) -> list[dict]:
    date_key = timestamp.astimezone(DISPLAY_TIMEZONE).date().isoformat()
    return list(WORK_TRACKING.setdefault("events", {}).get(f"{account_id}:{date_key}", []))


def worked_seconds(account_id: int, timestamp: datetime) -> int:
    total = 0.0
    active_since = None
    absences = tracking_account(account_id).get("official_absences", [])
    def effective_seconds(start: datetime, end: datetime) -> float:
        seconds = max(0.0, (end - start).total_seconds())
        for absence in absences:
            try:
                absence_start = datetime.fromisoformat(str(absence["starts_at"]))
                absence_end = datetime.fromisoformat(str(absence["ends_at"]))
            except (KeyError, ValueError, TypeError):
                continue
            overlap = max(0.0, (min(end, absence_end) - max(start, absence_start)).total_seconds())
            seconds -= overlap
        return max(0.0, seconds)
    for event in sorted(workday_events(account_id, timestamp), key=lambda item: item.get("at", "")):
        try:
            event_at = datetime.fromisoformat(str(event["at"]))
        except (KeyError, ValueError):
            continue
        if active_since is not None:
            total += effective_seconds(active_since, event_at)
            active_since = None
        if event.get("state") == "working":
            active_since = event_at
    if active_since is not None:
        total += effective_seconds(active_since, timestamp)
    return int(total)


def maybe_auto_finish(account_id: int, timestamp: datetime) -> None:
    item = tracking_account(account_id)
    bounds = schedule_bounds(account_id, timestamp)
    if bounds is None or item.get("work_state") != "working":
        return
    _, schedule_end = bounds
    if timestamp <= schedule_end:
        return
    try:
        last_active = datetime.fromisoformat(str(item.get("agent_last_active_at", "")))
    except ValueError:
        return
    if timestamp - last_active >= timedelta(minutes=30):
        set_work_state(account_id, "finished", "automatic_idle", timestamp=last_active)


def work_state_snapshot(account_id: int, timestamp: datetime | None = None) -> dict:
    timestamp = timestamp or now()
    maybe_auto_finish(account_id, timestamp)
    item = tracking_account(account_id)
    local_date = timestamp.astimezone(DISPLAY_TIMEZONE).date().isoformat()
    state = item.get("work_state") if item.get("work_state_date") == local_date else "not_started"
    official_absence = active_official_absence(account_id, timestamp)
    if official_absence is not None:
        state = official_absence["state"]
    reminder = ""
    agent_active = False
    try:
        seen = datetime.fromisoformat(str(item.get("agent_last_seen_at", "")))
        agent_active = timestamp - seen <= PRESENCE_ONLINE_TTL and not item.get("agent_locked") and int(item.get("agent_idle_seconds", 9999)) <= int(PRESENCE_ACTIVE_TTL.total_seconds())
    except ValueError:
        pass
    if state == "not_started":
        reminder = "Установите статус «Начать рабочий день», иначе рабочее время не будет засчитано."
    elif state in {"lunch", "break", "meeting", "other"} and agent_active:
        reminder = "Обнаружена рабочая активность. Установите статус «Вернуться к работе», иначе это время не будет засчитано."
    bounds = schedule_bounds(account_id, timestamp)
    scheduled_seconds = int((bounds[1] - bounds[0]).total_seconds()) if bounds else 0
    overtime = max(0, worked_seconds(account_id, timestamp) - scheduled_seconds) if scheduled_seconds else 0
    overtime += int(item.get("official_overtime", {}).get(local_date, 0))
    started_at = "—"
    for event in sorted(workday_events(account_id, timestamp), key=lambda item: item.get("at", "")):
        if event.get("state") == "working":
            try:
                started_at = datetime.fromisoformat(str(event["at"])).astimezone(DISPLAY_TIMEZONE).strftime("%H:%M:%S")
            except (KeyError, ValueError):
                pass
            break
    return {"state": state, "label": WORK_STATE_LABELS.get(state, state), "reminder": reminder, "overtime_seconds": overtime, "started_at": started_at}


def duration_label(seconds: int) -> str:
    hours, remainder = divmod(max(0, seconds), 3600)
    minutes = remainder // 60
    return f"{hours} ч {minutes:02d} мин"


def guest_language_session(request: web.Request, *, create: bool = True):
    guest_id = request.cookies.get(GUEST_LANGUAGE_COOKIE, "")
    session = GUEST_LANGUAGE_SESSIONS.get(guest_id)
    if session is not None and session.expires_at > now():
        return guest_id, session, False
    if guest_id:
        GUEST_LANGUAGE_SESSIONS.pop(guest_id, None)
    if not create:
        return "", None, False
    guest_id = secrets.token_urlsafe(24)
    session = GuestLanguageSession(
        csrf_token=secrets.token_urlsafe(24),
        language_code="ru",
        expires_at=now() + timedelta(hours=12),
    )
    GUEST_LANGUAGE_SESSIONS[guest_id] = session
    return guest_id, session, True


def guest_language_marker(code: str) -> Path:
    return LanguageRepository.language_dir(code) / ".guest-install-pending"


async def remove_interrupted_guest_language(job_id: str, job: GuestLanguageJob) -> bool:
    if job.package_preexisting:
        return False
    for other_id, other in GUEST_LANGUAGE_JOBS.items():
        if (
            other_id != job_id
            and other.language_code == job.language_code
            and other.status in {"queued", "running"}
            and other.last_seen_at + timedelta(seconds=4) > now()
        ):
            return False
    removed = await LanguageCleanupService.remove_if_unused(job.language_code)
    return removed


def active_guest_language_codes() -> set[str]:
    current = now()
    return {
        job.language_code
        for job in GUEST_LANGUAGE_JOBS.values()
        if job.status in {"queued", "running"}
        and job.last_seen_at + timedelta(seconds=4) > current
    }


async def cleanup_abandoned_guest_language_markers(application) -> None:
    for code in LanguageCleanupService.all_language_codes():
        marker = guest_language_marker(code)
        if marker.exists():
            await LanguageCleanupService.remove_if_unused(code)


async def persist_guest_language(request: web.Request, account_id: int) -> None:
    guest_id = request.get("guest_language_id", "")
    guest = request.get("guest_language_session")
    if guest is None:
        _, guest, _ = guest_language_session(request, create=False)
    if guest is None or not GuestLanguageService.installed(guest.language_code):
        return
    async with AsyncSessionLocal() as db:
        account = await db.get(Account, account_id)
        if account is not None and account.language != guest.language_code:
            account.language = guest.language_code
            await db.commit()
    if guest_id:
        GUEST_LANGUAGE_SESSIONS.pop(guest_id, None)


def normalize_email_domains(value: str | None) -> list[str]:
    result: list[str] = []
    for raw in re.split(r"[\s,;]+", value or ""):
        domain = raw.strip().casefold().lstrip("@.").rstrip(".")
        if not domain:
            continue
        try:
            domain = domain.encode("idna").decode("ascii")
        except UnicodeError as error:
            raise ValueError("Проверьте почтовые домены.") from error
        labels = domain.split(".")
        if (
            len(domain) > 253
            or len(labels) < 2
            or any(
                not label
                or len(label) > 63
                or label.startswith("-")
                or label.endswith("-")
                or re.fullmatch(r"[a-z0-9-]+", label) is None
                for label in labels
            )
        ):
            raise ValueError(f"Некорректный почтовый домен: {raw}")
        if domain not in result:
            result.append(domain)
    return result


def organization_email_domains(organization: Organization) -> list[str]:
    return normalize_email_domains(organization.allowed_email_domains)


def email_domain(email: str) -> str:
    return email.rsplit("@", 1)[1].encode("idna").decode("ascii").casefold()


def email_change_code_hash(account_id: int, email: str, code: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode(),
        f"email-change:{account_id}:{email}:{code}".encode(),
        hashlib.sha256,
    ).hexdigest()


async def account_primary_organization(db, account_id: int) -> Organization | None:
    return await db.scalar(
        select(Organization)
        .join(OrganizationalUnit, OrganizationalUnit.organization_id == Organization.id)
        .join(
            AccountOrganizationalUnitMembership,
            AccountOrganizationalUnitMembership.organizational_unit_id == OrganizationalUnit.id,
        )
        .where(
            AccountOrganizationalUnitMembership.account_id == account_id,
            AccountOrganizationalUnitMembership.is_active.is_(True),
            OrganizationalUnit.is_active.is_(True),
            Organization.is_active.is_(True),
        )
        .order_by(AccountOrganizationalUnitMembership.is_primary.desc())
        .limit(1)
    )


def icon_image(name: str) -> str:
    return (
        f'<img class="ui-icon" src="/static/icons/{name}.png" '
        'width="28" height="28" alt="" aria-hidden="true">'
    )


UI_ICON_REPLACEMENTS = {
    "🏢": "organizations",
    "🏛️": "holdings",
    "🏛": "holdings",
    "👥": "employees",
    "🎫": "tickets",
    "📊": "reports",
    "🔐": "access",
    "👤": "profile",
    "🌐": "language",
    "🏗️": "organizations",
    "🏗": "organizations",
    "🗺": "reports",
    "🔄": "reports",
    "➕": "organizations",
    "🔎": "reports",
    "📋": "reports",
    "✅": "access",
    "✏️": "reports",
    "✏": "reports",
    "📦": "holdings",
    "📜": "reports",
    "🕘": "reports",
    "🛡": "access",
    "🔑": "access",
}


def render_ui_icons(markup: str) -> str:
    for glyph in sorted(UI_ICON_REPLACEMENTS, key=len, reverse=True):
        markup = markup.replace(glyph, icon_image(UI_ICON_REPLACEMENTS[glyph]))
    return markup


def page(
    title: str,
    content: str,
    *,
    account: Account | None = None,
    active: str = "",
    body_class: str = "",
) -> web.Response:
    navigation = ""
    if account is not None:
        items = [
            ("organizations", "Организации"),
            ("holdings", "Холдинги"),
            ("employees", "Сотрудники"),
            ("tickets", "Тикеты"),
            ("reports", "Отчёты"),
            ("access", "Доступы"),
        ]
        links = "".join(
            f'<a class="nav-item {"active" if key == active else ""}" '
            f'href="/{key}"><span>{icon_image(key)}</span>{label}</a>'
            for key, label in items
        )
        navigation = (
            '<aside class="sidebar glass"><a class="logo" href="/">S</a>'
            f'<nav>{links}</nav></aside>'
        )

    shell_class = "app-shell" if account else "auth-shell"
    account_line = ""
    if account:
        initial = esc((account.full_name or "S").strip()[:1].upper())
        work_item = tracking_account(account.id)
        snapshot = work_state_snapshot(account.id)
        work_state = snapshot["state"]
        work_label = snapshot["label"]
        personal_label = "Работаю" if work_state == "working" else work_label
        action_labels = {"lunch": "Обед", "break": "Перерыв", "meeting": "Совещание", "other": "Прочая причина", "vacation": "Отпуск", "sick_leave": "Больничный", "business_trip": "Командировка", "day_off": "Отгул", "finished": "Завершить рабочий день"}
        working_action = "Начать рабочий день" if work_state in {"not_started", "finished"} else "Вернуться к работе"
        work_buttons = (f'<button type="button" data-work-state="working" class="account-work-action">{working_action}</button>'
            '<button type="button" class="account-work-action" data-open-absence-reasons>Покинуть рабочее место</button>'
            '<div class="account-absence-reasons" hidden><button type="button" class="account-work-back" data-close-absence-reasons>← Назад</button>'
            + "".join(f'<button type="button" data-work-state="{code}" class="account-work-action">{action_labels[code]}</button>' for code in ("lunch", "break", "meeting", "other")) + '</div>'
            '<button type="button" class="account-work-action" data-open-official-statuses>Официальное отсутствие</button>'
            '<div class="account-official-statuses" hidden><button type="button" class="account-work-back" data-close-official-statuses>← Назад</button>'
            + "".join(f'<button type="button" data-work-state="{code}" class="account-work-action">{action_labels[code]}</button>' for code in ("vacation", "sick_leave", "business_trip", "day_off")) + '</div>'
            f'<button type="button" data-work-state="finished" class="account-work-action">{action_labels["finished"]}</button>') if work_item.get("enabled") is not False else ""
        work_switch = f'<button type="button" class="account-menu-item account-status-switch" data-open-work-states><span class="account-menu-icon" aria-hidden="true">◉</span><span><b>Сменить статус</b><small class="account-work-current">{esc(work_label)}</small></span></button><div class="account-menu-divider"></div>' if work_buttons else ""
        work_screen = f'<div class="account-work-screen" hidden><button type="button" class="account-work-back" data-close-work-states>← Назад</button><span class="account-work-current">{esc(work_label)}</span><div class="account-work-controls">{work_buttons}</div></div>' if work_buttons else ""
        account_line = f'''<div class="account-menu">
<button class="account-menu-trigger" type="button" aria-expanded="false" aria-controls="account-menu-panel"><span class="account-avatar">{initial}</span><span class="account-trigger-copy"><b>{esc(account.full_name)}</b><small>{esc(get_role_name(account.role))}</small><span class="account-trigger-status" data-account-current-status>{esc(personal_label)}</span></span><span class="account-chevron" aria-hidden="true">›</span></button>
<section class="account-menu-panel glass" id="account-menu-panel" hidden>
<div class="account-menu-main">
<a class="account-menu-identity" href="/profile"><span class="account-avatar">{initial}</span><span><b>{esc(account.full_name)}</b><small>{esc(get_role_name(account.role))}</small></span><span class="account-chevron" aria-hidden="true">›</span></a>
<div class="account-menu-divider"></div>
{work_switch}
<div class="account-menu-theme"><span class="account-menu-icon" aria-hidden="true">◐</span><span>Внешний вид</span><div class="theme-switch account-theme-switch" role="group" aria-label="Тема оформления"><button type="button" class="theme-switch-button" data-theme-choice="day" aria-pressed="false" title="Светлая тема">☀</button><button type="button" class="theme-switch-button" data-theme-choice="night" aria-pressed="false" title="Тёмная тема">☾</button><button type="button" class="theme-switch-button" data-theme-choice="auto" aria-pressed="false" title="Автоматически">◷</button></div></div>
<a class="account-menu-item" href="/profile"><span class="account-menu-icon" aria-hidden="true">○</span><span>Профиль</span></a>
<a class="account-menu-item" href="/language"><span class="account-menu-icon" aria-hidden="true">◎</span><span>Язык интерфейса</span></a>
<div class="account-menu-divider"></div>
<a class="account-menu-item account-menu-logout" href="/logout"><span class="account-menu-icon" aria-hidden="true">↪</span><span>Выйти</span></a>
</div>{work_screen}
</section></div>'''
    page_actions = ""
    if account:
        actions_html = ""
        action_match = re.match(
            r'^<div class="action-bar(?: [^"]*)?">(.*?)</div>',
            content,
            flags=re.DOTALL,
        )
        if action_match:
            actions_html = re.sub(
                r'<a\b[^>]*>(?:(?!</a>).)*(?:Назад|На главную)(?:(?!</a>).)*</a>',
                "",
                action_match.group(1),
                flags=re.DOTALL | re.IGNORECASE,
            )
            content = content[action_match.end():]
        embedded_actions = re.search(
            r'<aside class="organization-actions glass"><h3>Действия</h3>(.*?)</aside>',
            content,
            flags=re.DOTALL,
        )
        if embedded_actions:
            if not actions_html.strip():
                actions_html = embedded_actions.group(1)
            content = content[:embedded_actions.start()] + content[embedded_actions.end():]
        empty_class = "" if actions_html.strip() else " is-empty"
        empty_message = "" if actions_html.strip() else '<p class="page-actions-empty">Нет доступных действий</p>'
        page_actions = (
            f'<aside class="page-actions glass{empty_class}" aria-label="Действия">'
            '<h3>Действия</h3>' + actions_html + empty_message + "</aside>"
        )
        content = (
            '<div class="workspace-layout"><div class="workspace-content">'
            + content + "</div>" + page_actions + "</div>"
        )
    navigation = render_ui_icons(navigation)
    content = render_ui_icons(content)
    login_effect = (
        '<canvas class="login-wave-canvas" aria-hidden="true"></canvas>'
        '<script src="/static/wave-grid.js?v=20260722-15" defer></script>'
        '<script src="/static/login-methods.js?v=20260722-1" defer></script>'
        if body_class == "login-page"
        else ""
    )
    theme_switch = '''<div class="theme-switch guest-theme-switch" role="group" aria-label="Тема оформления">
<button type="button" class="theme-switch-button" data-theme-choice="day" aria-pressed="false" title="Светлая тема"><span aria-hidden="true">☀</span><span>День</span></button>
<button type="button" class="theme-switch-button" data-theme-choice="night" aria-pressed="false" title="Тёмная тема"><span aria-hidden="true">☾</span><span>Ночь</span></button>
<button type="button" class="theme-switch-button" data-theme-choice="auto" aria-pressed="false" title="По времени компьютера"><span aria-hidden="true">◷</span><span>Авто</span></button>
</div>'''
    if account:
        theme_switch = ""
    document = f"""<!doctype html>
<html lang="ru" data-theme="night" data-theme-mode="auto"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#090b0e">
<title>{esc(title)} · SupportBot Enterprise</title>
<script>(function(){{var m="auto";try{{m=localStorage.getItem("supportbot-theme-mode")||"auto";}}catch(e){{}}if(m!=="day"&&m!=="night"&&m!=="auto")m="auto";var h=new Date().getHours(),t=m==="auto"?(h>=7&&h<20?"day":"night"):m;document.documentElement.setAttribute("data-theme-mode",m);document.documentElement.setAttribute("data-theme",t);}}());</script>
<link rel="stylesheet" href="/styles.css?v=20260722-88"><script src="/static/theme-switcher.js?v=20260722-2" defer></script><script src="/static/account-menu.js?v=20260722-7" defer></script><script src="/static/code-auto-submit.js?v=20260722-1" defer></script><script src="/static/update-notice.js?v=20260722-1" defer></script>{agent_page_assets(account)}</head>
<body class="{esc(body_class)}"><div class="wallpaper"><span class="orb orb-one"></span>
<span class="orb orb-two"></span><span class="orb orb-three"></span></div>{login_effect}
{theme_switch}<div class="{shell_class}">{navigation}<main class="workspace">
<header class="workspace-header"><div><div class="eyebrow">SupportBot Enterprise</div>
<h1>{esc(title)}</h1></div>{account_line}</header>{content}</main></div></body></html>"""
    return web.Response(text=document, content_type="text/html", charset="utf-8")


def agent_page_assets(account: Account | None) -> str:
    if account is None:
        return ""
    tracking = tracking_account(account.id)
    config = {
        "enabled": tracking.get("enabled") is not False,
        "serverUrl": WEB_PUBLIC_URL,
        "token": tracking.get("token", ""),
        "agentVersion": "test-0.3.3",
        "serverSeenVersion": tracking.get("agent_version", ""),
        "windowsDownload": "/static/agents/SupportBot-Presence-Setup-test.exe",
        "macDownload": "/static/agents/SupportBot-Presence-Setup-test.pkg",
    }
    encoded = json.dumps(config).replace("</", "<\\/")
    return (
        '<script src="/static/presence.js?v=20260722-3" defer></script>'
        f'<script>window.supportBotAgentConfig={encoded};</script>'
        '<script src="/static/agent-enrollment.js?v=20260722-7" defer></script>'
    )


def error_page(message: str, *, status: int = 400, account=None) -> web.Response:
    response = page(
        "Ошибка",
        f'<section class="panel glass"><p>{esc(message)}</p>'
        '<a class="button" href="/">На главную</a></section>',
        account=account,
    )
    response.set_status(status)
    return response


def search_form(action: str, value: str, placeholder: str) -> str:
    return (
        f'<form class="search glass" method="get" action="{esc(action)}">'
        f'<input name="q" value="{esc(value)}" placeholder="{esc(placeholder)}">'
        '<button type="submit">Найти</button></form>'
    )


def cards(items: list[str], empty: str = "Ничего не найдено") -> str:
    if not items:
        return f'<section class="empty glass">{esc(empty)}</section>'
    return f'<section class="data-grid">{"".join(items)}</section>'


async def current_account(request: web.Request) -> Account | None:
    token = request.cookies.get(SESSION_COOKIE)
    session = WEB_SESSIONS.get(token or "")
    if session is None or session.expires_at <= now():
        if token:
            WEB_SESSIONS.pop(token, None)
            save_web_sessions()
        return None
    async with AsyncSessionLocal() as db:
        account = await db.scalar(
            select(Account).where(
                Account.id == session.account_id,
                Account.is_active.is_(True),
                Account.registered.is_(True),
            )
        )
        return account


@web.middleware
async def account_middleware(request: web.Request, handler):
    request["account"] = await current_account(request)
    public = request.path in {
        "/login",
        "/auth/email",
        "/auth/request",
        "/auth/verify",
        "/auth/recovery",
        "/auth/recovery/request",
        "/auth/recovery/verify",
        "/auth/recovery/password",
        "/register",
        "/styles.css",
        "/app.js",
        "/api/version",
    }
    public = public or request.path.startswith("/static/")
    public = public or request.path.startswith("/auth/2fa/")
    public = public or request.path.startswith("/auth/language")
    public = public or request.path == "/api/1c/auth/email"
    public = public or request.path == "/api/agent/heartbeat"
    public = public or request.path == "/api/agent/work-state"
    public = public or request.path.startswith("/auth/1c/exchange/")
    if request["account"] is None and not public:
        raise web.HTTPFound("/login")
    return await handler(request)


@web.middleware
async def guest_language_middleware(request: web.Request, handler):
    guest_paths = (
        request.path == "/login"
        or request.path == "/register"
        or request.path.startswith("/auth/")
    )
    if not guest_paths:
        return await handler(request)
    guest_id, guest, created = guest_language_session(request)
    request["guest_language_id"] = guest_id
    request["guest_language_session"] = guest
    try:
        response = await handler(request)
    except web.HTTPException as exception:
        response = exception
        raised = True
    else:
        raised = False
    if (
        isinstance(response, web.Response)
        and response.content_type == "text/html"
        and response.body
        and guest is not None
    ):
        response.text = GuestLanguageService.translate_html(response.text, guest.language_code)
        response.headers["Content-Language"] = guest.language_code
    if created:
        response.set_cookie(
            GUEST_LANGUAGE_COOKIE,
            guest_id,
            httponly=True,
            samesite="Lax",
            path="/",
        )
    if raised:
        raise response
    return response


@web.middleware
async def embedded_client_middleware(request: web.Request, handler):
    embedded = (
        request.query.get("embedded") == "1c"
        or request.cookies.get(EMBEDDED_COOKIE) == "1c"
    )
    request["embedded_1c"] = embedded
    raised_response = False
    try:
        response = await handler(request)
    except web.HTTPException as exception:
        response = exception
        raised_response = True

    if embedded:
        response.set_cookie(
            EMBEDDED_COOKIE,
            "1c",
            max_age=365 * 24 * 60 * 60,
            path="/",
            samesite="Lax",
        )
        if (
            isinstance(response, web.Response)
            and response.content_type == "text/html"
            and response.body
        ):
            document = response.text.replace(
                '<html lang="ru"',
                '<html class="embedded-1c" lang="ru"',
                1,
            )
            response.text = document

    if raised_response:
        raise response
    return response


@web.middleware
async def response_performance_middleware(request: web.Request, handler):
    response = await handler(request)
    if request.path.startswith("/auth/2fa/"):
        response.headers["Cache-Control"] = "no-store"
    elif request.path in {"/styles.css", "/app.js"} or request.path.startswith(
        "/static/"
    ):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return response


def authenticated(
    handler: Callable[[web.Request, Account], Awaitable[web.StreamResponse]],
):
    async def wrapped(request: web.Request):
        account = request["account"]
        if account is None:
            raise web.HTTPFound("/login")
        return await handler(request, account)

    return wrapped


async def can(account: Account, permission: Permission) -> bool:
    return await AuthorizationService.can_async(account, permission)


async def login_page(request: web.Request) -> web.Response:
    if request["account"]:
        raise web.HTTPFound("/")
    content = """<section class="login-card glass hybrid-login"><div class="login-logo">S</div>
<h2>Вход в кабинет</h2><p>Выберите удобный способ входа.</p>
<div class="auth-methods">
<section class="auth-method"><button type="button" class="auth-method-toggle" aria-expanded="false" aria-controls="email-login-panel"><span>Войти по email и паролю</span><span class="auth-method-chevron" aria-hidden="true">+</span></button>
<div class="auth-method-panel" id="email-login-panel"><form method="post" action="/auth/email"><label>Email</label>
<input type="email" name="email" required autocomplete="username">
<label>Пароль</label><input type="password" name="password" required autocomplete="current-password">
<button type="submit">Войти в кабинет</button>
<a class="forgot-password" href="/auth/recovery">Не помню пароль</a></form></div></section>
<section class="auth-method"><button type="button" class="auth-method-toggle" aria-expanded="false" aria-controls="telegram-login-panel"><span>Войти через Telegram</span><span class="auth-method-chevron" aria-hidden="true">+</span></button>
<div class="auth-method-panel" id="telegram-login-panel"><form method="post" action="/auth/request"><label>Telegram ID</label>
<input name="telegram_id" inputmode="numeric" required>
<button type="submit" class="secondary">Получить код в Telegram</button></form></div></section>
</div><a class="auth-language-button" href="/auth/language"><span aria-hidden="true">🌐</span><span>Выбрать язык</span></a></section>"""
    return page("Вход", content, body_class="login-page")


def establish_session(account_id: int) -> tuple[str, WebSession]:
    token = secrets.token_urlsafe(32)
    logged_in_at = now()
    session = WebSession(
        account_id=account_id,
        csrf_token=secrets.token_urlsafe(24),
        expires_at=logged_in_at + SESSION_TTL,
        login_at=logged_in_at,
        last_seen_at=logged_in_at,
        last_activity_at=logged_in_at,
    )
    WEB_SESSIONS[token] = session
    save_web_sessions()
    LAST_LOGIN_TIMES[account_id] = logged_in_at
    save_login_times()
    record_workday_start(account_id, logged_in_at)
    return token, session


def _create_authenticated_session(account_id: int) -> web.Response:
    token, _ = establish_session(account_id)
    response = web.HTTPFound("/")
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="Strict",
        max_age=int(SESSION_TTL.total_seconds()),
        path="/",
    )
    return response


def create_two_factor_challenge(account_id: int, *, embedded: bool = False) -> str:
    token = secrets.token_urlsafe(32)
    TWO_FACTOR_CHALLENGES[token] = TwoFactorChallenge(
        account_id=account_id,
        expires_at=now() + timedelta(minutes=15),
        embedded=embedded,
    )
    return token


def begin_two_factor_login_response(request: web.Request, account_id: int) -> web.Response:
    token = create_two_factor_challenge(
        account_id,
        embedded=bool(request.get("embedded_1c")),
    )
    suffix = "?embedded=1c" if request.get("embedded_1c") else ""
    raise web.HTTPFound(f"/auth/2fa/{token}{suffix}")


def get_two_factor_challenge(token: str) -> TwoFactorChallenge | None:
    challenge = TWO_FACTOR_CHALLENGES.get(token)
    if challenge is None or challenge.expires_at <= now():
        TWO_FACTOR_CHALLENGES.pop(token, None)
        return None
    return challenge


async def email_login(request: web.Request) -> web.Response:
    form = await request.post()
    try:
        email = WebIdentityService.normalize_email(str(form.get("email", "")))
    except ValueError:
        return error_page("Неверный email или пароль.", status=403)
    password = str(form.get("password", ""))
    async with AsyncSessionLocal() as db:
        account = await db.scalar(
            select(Account).where(
                func.lower(Account.email) == email,
                Account.is_active.is_(True),
                Account.registered.is_(True),
                Account.email_verified_at.is_not(None),
            )
        )
        valid = account is not None and WebIdentityService.verify_password(
            password,
            account.password_hash,
        )
        if valid:
            account.last_login = now()
            await db.commit()
    if not valid:
        return error_page("Неверный email или пароль.", status=403)
    return begin_two_factor_login_response(request, account.id)


async def is_platform_admin(db, account: Account) -> bool:
    if account.role == UserRole.ADMIN:
        return True
    assignment = await db.scalar(
        select(RoleAssignment.id)
        .join(Role, Role.id == RoleAssignment.role_id)
        .where(
            RoleAssignment.account_id == account.id,
            RoleAssignment.is_active.is_(True),
            RoleAssignment.revoked_at.is_(None),
            RoleAssignment.scope_type == ScopeType.PLATFORM,
            Role.code == "platform_admin",
        )
        .limit(1)
    )
    return assignment is not None


async def can_reset_two_factor(db, account: Account) -> bool:
    if await is_platform_admin(db, account) or account.role == UserRole.OPERATOR:
        return True
    assignment = await db.scalar(
        select(RoleAssignment.id)
        .join(Role, Role.id == RoleAssignment.role_id)
        .where(
            RoleAssignment.account_id == account.id,
            RoleAssignment.is_active.is_(True),
            RoleAssignment.revoked_at.is_(None),
            Role.code == "operator",
        )
        .limit(1)
    )
    return assignment is not None


async def can_reset_two_factor_for(db, actor: Account, target: Account) -> bool:
    if not await can_reset_two_factor(db, actor):
        return False
    if await is_platform_admin(db, actor):
        return True
    if await is_platform_admin(db, target):
        return False
    return await access_target_allowed(db, actor, target.id)


def revoke_account_authentication(account_id: int) -> None:
    for token, session in list(WEB_SESSIONS.items()):
        if session.account_id == account_id:
            WEB_SESSIONS.pop(token, None)
    for token, challenge in list(TWO_FACTOR_CHALLENGES.items()):
        if challenge.account_id == account_id:
            TWO_FACTOR_CHALLENGES.pop(token, None)
    for token, challenge in list(LOGIN_CHALLENGES.items()):
        if challenge.account_id == account_id:
            LOGIN_CHALLENGES.pop(token, None)
    save_web_sessions()


def admin_recovery_code_hash(account_id: int, code: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode(),
        f"admin-2fa-recovery:{account_id}:{code}".encode(),
        hashlib.sha256,
    ).hexdigest()


def two_factor_error(message: str, *, status: int = 403) -> web.Response:
    response = page(
        "Двухфакторная аутентификация",
        f'<section class="login-card glass hybrid-login recovery-card"><div class="login-logo">S</div>'
        f'<h2>Не удалось продолжить</h2><p>{esc(message)}</p>'
        '<a class="forgot-password recovery-back" href="/login">Вернуться ко входу</a></section>',
        body_class="login-page",
    )
    response.set_status(status)
    return response


async def admin_two_factor_recovery_page(request: web.Request) -> web.Response:
    content = """<section class="login-card glass hybrid-login recovery-card two-factor-card"><div class="login-logo">S</div>
<h2>Аварийный доступ администратора</h2><p>Этот способ доступен только платформенному администратору, потерявшему телефон и резервные коды. Потребуются действующий пароль и доступ к подтверждённой служебной почте.</p>
<form method="post" action="/auth/2fa/admin-recovery/request"><label>Рабочий email</label>
<input type="email" name="email" required autocomplete="username" autofocus>
<label>Пароль</label><input type="password" name="password" required autocomplete="current-password">
<button type="submit">Отправить защитный код</button></form>
<p class="recovery-hint">После подтверждения текущая 2FA будет сброшена, но вход останется заблокирован до настройки нового приложения.</p>
<a class="forgot-password recovery-back" href="/login">Вернуться ко входу</a></section>"""
    return page("Аварийный доступ", content, body_class="login-page")


async def admin_two_factor_recovery_request(request: web.Request) -> web.Response:
    form = await request.post()
    raw_email = str(form.get("email", ""))
    password = str(form.get("password", ""))
    recovery_id = ""
    try:
        email = WebIdentityService.normalize_email(raw_email)
    except ValueError:
        email = ""
    async with AsyncSessionLocal() as db:
        account = None
        if email:
            account = await db.scalar(
                select(Account).where(
                    func.lower(Account.email) == email,
                    Account.is_active.is_(True),
                    Account.registered.is_(True),
                    Account.email_verified_at.is_not(None),
                )
            )
        password_hash = (
            account.password_hash
            if account is not None and account.password_hash
            else "$2b$12$jECn/IaSGMxxCqpEqk9GVOGUoCwC1RvLbGaO.x9GTQQSKNqoqiysi"
        )
        password_valid = WebIdentityService.verify_password(password, password_hash)
        valid = (
            account is not None
            and await is_platform_admin(db, account)
            and password_valid
        )
        if valid:
            last_sent = ADMIN_2FA_RECOVERY_LAST_SENT.get(account.id)
            if last_sent is None or last_sent <= now() - timedelta(seconds=60):
                code = f"{secrets.randbelow(1_000_000):06d}"
                recovery_id = secrets.token_urlsafe(32)
                ADMIN_2FA_RECOVERY_CHALLENGES[recovery_id] = AdminTwoFactorRecoveryChallenge(
                    account_id=account.id,
                    code_hash=admin_recovery_code_hash(account.id, code),
                    expires_at=now() + timedelta(minutes=10),
                )
                try:
                    await WebIdentityService(db).send_email(
                        recipient=account.email,
                        subject="Аварийный сброс 2FA — SupportBot Enterprise",
                        text=(
                            f"Здравствуйте, {account.full_name}!\n\n"
                            f"Код аварийного сброса 2FA: {code}\n\n"
                            "Код действует 10 минут. После его ввода потребуется заново настроить 2FA.\n"
                            "Если вы не запрашивали сброс, немедленно обратитесь к другому администратору."
                        ),
                        html=(
                            '<div style="background:#090b0e;padding:32px;color:#f7f2e8;font-family:Arial,sans-serif">'
                            '<div style="max-width:560px;margin:auto;background:#171b21;border:1px solid #65583f;border-radius:20px;padding:36px">'
                            '<h1 style="color:#f7f2e8">Аварийный сброс 2FA</h1>'
                            f'<p style="color:#c8c1b5">Здравствуйте, {esc(account.full_name)}!</p>'
                            '<p style="color:#c8c1b5">Введите этот код для сброса потерянного второго фактора:</p>'
                            f'<div style="padding:20px;text-align:center;background:#0d1116;border-radius:14px;color:#e4c78f;font-size:32px;font-weight:bold;letter-spacing:8px">{code}</div>'
                            '<p style="color:#c8c1b5">Код действует 10 минут. После сброса необходимо заново настроить 2FA.</p>'
                            '<p style="color:#a59e92;font-size:13px">Если вы не запрашивали сброс, немедленно обратитесь к другому администратору.</p>'
                            '</div></div>'
                        ),
                    )
                    ADMIN_2FA_RECOVERY_LAST_SENT[account.id] = now()
                except Exception:
                    ADMIN_2FA_RECOVERY_CHALLENGES.pop(recovery_id, None)
                    recovery_id = ""
                    logger.exception("Failed to send admin 2FA recovery code")

    content = f"""<section class="login-card glass hybrid-login recovery-card two-factor-card"><div class="login-logo">S</div>
<h2>Проверьте служебную почту</h2><p>Если данные платформенного администратора подтверждены и почта настроена, защитный код отправлен.</p>
<form method="post" action="/auth/2fa/admin-recovery/verify" data-auto-code-form>
<input type="hidden" name="challenge" value="{esc(recovery_id)}">
<label>Шестизначный защитный код</label><input name="code" inputmode="numeric" pattern="[0-9]{{6}}" maxlength="6" required autocomplete="one-time-code" autofocus data-auto-code>
</form>
<p class="recovery-hint">Ответ страницы одинаков для существующих и несуществующих аккаунтов.</p></section>"""
    return page("Аварийное подтверждение", content, body_class="login-page")


async def admin_two_factor_recovery_verify(request: web.Request) -> web.Response:
    form = await request.post()
    recovery_id = str(form.get("challenge", ""))
    code = str(form.get("code", "")).strip()
    challenge = ADMIN_2FA_RECOVERY_CHALLENGES.get(recovery_id)
    if challenge is None or challenge.expires_at <= now():
        ADMIN_2FA_RECOVERY_CHALLENGES.pop(recovery_id, None)
        return two_factor_error("Защитный код недействителен или истёк.")
    challenge.attempts += 1
    if challenge.attempts > 5:
        ADMIN_2FA_RECOVERY_CHALLENGES.pop(recovery_id, None)
        return two_factor_error("Превышено число попыток.")
    if not hmac.compare_digest(
        admin_recovery_code_hash(challenge.account_id, code),
        challenge.code_hash,
    ):
        return two_factor_error("Защитный код недействителен или истёк.")

    async with AsyncSessionLocal() as db:
        account = await db.get(Account, challenge.account_id)
        if account is None or not await is_platform_admin(db, account):
            return two_factor_error("Аварийный сброс недоступен.")
        setting = await db.get(TwoFactorSetting, account.id)
        previous_provider = setting.provider if setting else None
        if setting is not None:
            await db.delete(setting)
        db.add(
            AccessAuditEvent(
                event_type="two_factor_emergency_reset",
                actor_account_id=account.id,
                target_account_id=account.id,
                details={"method": "password_and_verified_email", "previous_provider": previous_provider},
            )
        )
        await db.commit()
    ADMIN_2FA_RECOVERY_CHALLENGES.pop(recovery_id, None)
    revoke_account_authentication(challenge.account_id)
    token = create_two_factor_challenge(challenge.account_id, embedded=bool(request.get("embedded_1c")))
    suffix = "?embedded=1c" if request.get("embedded_1c") else ""
    raise web.HTTPFound(f"/auth/2fa/{token}{suffix}")


def two_factor_provider_instructions(provider: str) -> str:
    instructions = {
        "yandex": (
            "Откройте Яндекс Ключ. Нажмите знак «+», выберите добавление аккаунта "
            "по QR-коду и разрешите доступ к камере."
        ),
        "microsoft": (
            "Откройте Microsoft Authenticator. Нажмите «+», выберите «Другая учётная запись», "
            "затем выберите сканирование QR-кода."
        ),
        "google": (
            "Откройте Google Authenticator. Нажмите «+» и выберите «Сканировать QR-код»."
        ),
    }
    return instructions[provider]


async def two_factor_start(request: web.Request) -> web.Response:
    token = request.match_info["token"]
    challenge = get_two_factor_challenge(token)
    if challenge is None:
        return two_factor_error("Сеанс настройки истёк. Выполните вход ещё раз.")
    async with AsyncSessionLocal() as db:
        account = await db.get(Account, challenge.account_id)
        setting = await db.get(TwoFactorSetting, challenge.account_id)
        platform_admin = await is_platform_admin(db, account) if account is not None else False
    if account is None or not account.is_active or not account.registered:
        return two_factor_error("Аккаунт недоступен.")
    if setting is not None and setting.is_enabled:
        content = f"""<section class="login-card glass hybrid-login recovery-card two-factor-card"><div class="login-logo">S</div>
<h2>Подтвердите вход</h2><p>Введите шестизначный код из {esc(TwoFactorService.PROVIDERS.get(setting.provider, 'приложения-аутентификатора'))} или один резервный код.</p>
<form method="post" action="/auth/2fa/{esc(token)}/verify" data-auto-code-form><label>Код подтверждения</label>
<input name="code" required autocomplete="one-time-code" autofocus data-auto-code data-allow-recovery-code>
</form>
<p class="recovery-hint">Код из приложения обновляется каждые 30 секунд. Один и тот же код нельзя использовать повторно.</p>
<p class="recovery-hint">Потеряли телефон? Используйте резервный код или обратитесь к платформенному администратору либо оператору.</p>
{('<a class="forgot-password recovery-back" href="/auth/2fa/admin-recovery">Аварийный доступ платформенного администратора</a>' if platform_admin else '')}</section>"""
        return page("Подтверждение входа", content, body_class="login-page")

    provider_buttons = "".join(
        f'<button type="submit" name="provider" value="{esc(code)}" class="two-factor-provider">'
        f'<strong>{esc(label)}</strong><span>Настроить приложение</span></button>'
        for code, label in TwoFactorService.PROVIDERS.items()
    )
    content = f"""<section class="login-card glass hybrid-login recovery-card two-factor-card"><div class="login-logo">S</div>
<h2>Защитите аккаунт</h2><p>Двухфакторная аутентификация обязательна. Выберите приложение, которым будете подтверждать каждый вход.</p>
<div class="two-factor-steps"><b>Шаг 1 из 3</b><span>Выбор приложения</span></div>
<form class="provider-form" method="post" action="/auth/2fa/{esc(token)}/provider">{provider_buttons}</form>
<p class="recovery-hint">До завершения всех трёх шагов доступ к кабинету закрыт.</p></section>"""
    return page("Настройка 2FA", content, body_class="login-page")


async def two_factor_select_provider(request: web.Request) -> web.Response:
    token = request.match_info["token"]
    challenge = get_two_factor_challenge(token)
    if challenge is None:
        return two_factor_error("Сеанс настройки истёк. Выполните вход ещё раз.")
    form = await request.post()
    provider = str(form.get("provider", ""))
    async with AsyncSessionLocal() as db:
        try:
            await TwoFactorService(db).start_enrollment(challenge.account_id, provider)
        except ValueError as error:
            return two_factor_error(str(error), status=400)
    suffix = "?embedded=1c" if challenge.embedded else ""
    raise web.HTTPFound(f"/auth/2fa/{token}/setup{suffix}")


async def two_factor_setup(request: web.Request) -> web.Response:
    token = request.match_info["token"]
    challenge = get_two_factor_challenge(token)
    if challenge is None:
        return two_factor_error("Сеанс настройки истёк. Выполните вход ещё раз.")
    async with AsyncSessionLocal() as db:
        account = await db.get(Account, challenge.account_id)
        setting = await db.get(TwoFactorSetting, challenge.account_id)
        if account is None or setting is None or setting.is_enabled:
            return two_factor_error("Начните настройку заново.")
        secret = TwoFactorService.secret(setting)
    instruction = two_factor_provider_instructions(setting.provider)
    provider_name = TwoFactorService.PROVIDERS[setting.provider]
    content = f"""<section class="login-card glass hybrid-login recovery-card two-factor-card"><div class="login-logo">S</div>
<h2>Подключите {esc(provider_name)}</h2>
<div class="two-factor-steps"><b>Шаг 2 из 3</b><span>Добавление аккаунта</span></div>
<ol class="setup-instructions"><li>Установите и откройте {esc(provider_name)} на телефоне.</li><li>{esc(instruction)}</li><li>Наведите камеру на QR-код ниже. Если сканирование недоступно, выберите ручной ввод и укажите ключ.</li><li>После добавления аккаунта приложение покажет шестизначный код. Введите его в форму.</li></ol>
<img class="two-factor-qr" src="/auth/2fa/{esc(token)}/qr" width="220" height="220" alt="QR-код для настройки">
<div class="manual-secret"><span>Ключ для ручного ввода</span><code>{esc(secret)}</code></div>
<form method="post" action="/auth/2fa/{esc(token)}/confirm" data-auto-code-form><label>Код из приложения</label>
<input name="code" inputmode="numeric" pattern="[0-9]{{6}}" maxlength="6" required autocomplete="one-time-code" autofocus data-auto-code>
</form>
<p class="recovery-hint">Не удаляйте аккаунт из приложения после проверки — код потребуется при каждом входе.</p></section>"""
    return page("Подключение 2FA", content, body_class="login-page")


async def two_factor_qr(request: web.Request) -> web.Response:
    token = request.match_info["token"]
    challenge = get_two_factor_challenge(token)
    if challenge is None:
        raise web.HTTPNotFound()
    async with AsyncSessionLocal() as db:
        account = await db.get(Account, challenge.account_id)
        setting = await db.get(TwoFactorSetting, challenge.account_id)
        if account is None or setting is None or setting.is_enabled:
            raise web.HTTPNotFound()
        uri = TwoFactorService.provisioning_uri(
            TwoFactorService.secret(setting),
            account.email or str(account.telegram_id or account.id),
        )
    image = qrcode.make(uri)
    output = BytesIO()
    image.save(output, format="PNG")
    return web.Response(
        body=output.getvalue(),
        content_type="image/png",
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )


async def two_factor_confirm_enrollment(request: web.Request) -> web.Response:
    token = request.match_info["token"]
    challenge = get_two_factor_challenge(token)
    if challenge is None:
        return two_factor_error("Сеанс настройки истёк. Выполните вход ещё раз.")
    challenge.attempts += 1
    if challenge.attempts > 8:
        TWO_FACTOR_CHALLENGES.pop(token, None)
        return two_factor_error("Превышено число попыток. Выполните вход ещё раз.")
    form = await request.post()
    code = str(form.get("code", "")).strip()
    async with AsyncSessionLocal() as db:
        setting = await db.get(TwoFactorSetting, challenge.account_id)
        if setting is None or setting.is_enabled:
            return two_factor_error("Начните настройку заново.")
        if not await TwoFactorService(db).verify_enrollment(setting, code):
            return two_factor_error("Код не подошёл. Проверьте время на телефоне и повторите настройку.", status=400)
    challenge.recovery_codes = TwoFactorService.generate_recovery_codes()
    codes = "".join(f"<code>{esc(code)}</code>" for code in challenge.recovery_codes)
    content = f"""<section class="login-card glass hybrid-login recovery-card two-factor-card"><div class="login-logo">S</div>
<h2>Сохраните резервные коды</h2>
<div class="two-factor-steps"><b>Шаг 3 из 3</b><span>Защита от потери телефона</span></div>
<p>Каждый резервный код позволяет войти один раз, если телефон недоступен. Сохраните их в менеджере паролей или распечатайте.</p>
<div class="recovery-codes">{codes}</div>
<form method="post" action="/auth/2fa/{esc(token)}/activate">
<label class="recovery-confirm"><input type="checkbox" name="saved" value="yes" required> Я сохранил резервные коды в безопасном месте</label>
<button type="submit">Завершить настройку и войти</button></form>
<p class="recovery-hint">После завершения этот список больше не будет показан. Не храните его вместе с телефоном.</p></section>"""
    return page("Резервные коды", content, body_class="login-page")


async def two_factor_activate(request: web.Request) -> web.Response:
    token = request.match_info["token"]
    challenge = get_two_factor_challenge(token)
    if challenge is None or not challenge.recovery_codes:
        return two_factor_error("Сначала подтвердите код из приложения.")
    form = await request.post()
    if form.get("saved") != "yes":
        return two_factor_error("Подтвердите сохранение резервных кодов.", status=400)
    async with AsyncSessionLocal() as db:
        setting = await db.get(TwoFactorSetting, challenge.account_id)
        if setting is None or setting.is_enabled:
            return two_factor_error("Настройка уже завершена или недоступна.")
        await TwoFactorService(db).activate(setting, challenge.recovery_codes, now())
    await persist_guest_language(request, challenge.account_id)
    TWO_FACTOR_CHALLENGES.pop(token, None)
    response = _create_authenticated_session(challenge.account_id)
    response.del_cookie(GUEST_LANGUAGE_COOKIE, path="/")
    return response


async def two_factor_verify_login(request: web.Request) -> web.Response:
    token = request.match_info["token"]
    challenge = get_two_factor_challenge(token)
    if challenge is None:
        return two_factor_error("Сеанс подтверждения истёк. Выполните вход ещё раз.")
    challenge.attempts += 1
    if challenge.attempts > 8:
        TWO_FACTOR_CHALLENGES.pop(token, None)
        return two_factor_error("Превышено число попыток. Выполните вход ещё раз.")
    form = await request.post()
    code = str(form.get("code", ""))
    async with AsyncSessionLocal() as db:
        setting = await db.get(TwoFactorSetting, challenge.account_id)
        if setting is None or not setting.is_enabled:
            return two_factor_error("Двухфакторная аутентификация не настроена.")
        valid = await TwoFactorService(db).verify_login(setting, code)
    if not valid:
        return two_factor_error("Неверный, просроченный или уже использованный код.", status=403)
    await persist_guest_language(request, challenge.account_id)
    TWO_FACTOR_CHALLENGES.pop(token, None)
    response = _create_authenticated_session(challenge.account_id)
    response.del_cookie(GUEST_LANGUAGE_COOKIE, path="/")
    return response


async def password_recovery_page(request: web.Request) -> web.Response:
    if request["account"]:
        raise web.HTTPFound("/")
    content = """<section class="login-card glass hybrid-login recovery-card"><div class="login-logo">S</div>
<h2>Одноразовый доступ</h2><p>Укажите рабочий email сотрудника. Мы отправим код для входа, если адрес найден и почта настроена.</p>
<form method="post" action="/auth/recovery/request"><label>Email</label>
<input type="email" name="email" required autocomplete="email" autofocus>
<button type="submit">Отправить код</button></form>
<a class="forgot-password recovery-back" href="/login">Вернуться ко входу</a></section>"""
    return page("Одноразовый доступ", content, body_class="login-page")


async def password_recovery_request(request: web.Request) -> web.Response:
    form = await request.post()
    raw_email = str(form.get("email", ""))
    try:
        email = WebIdentityService.normalize_email(raw_email)
    except ValueError:
        email = ""

    if email:
        async with AsyncSessionLocal() as db:
            try:
                sent = await PasswordRecoveryService(db).request_code(email)
                if sent:
                    await db.commit()
                else:
                    await db.rollback()
            except Exception:
                await db.rollback()
                logger.exception("Failed to send password access code")

    content = f"""<section class="login-card glass hybrid-login recovery-card"><div class="login-logo">S</div>
<h2>Проверьте почту</h2><p>Если сотрудник с таким email найден и почтовый сервис настроен, письмо с кодом уже отправлено.</p>
<form method="post" action="/auth/recovery/verify" data-auto-code-form><label>Email</label>
<input type="email" name="email" value="{esc(email or raw_email)}" required autocomplete="email">
<label>Одноразовый код</label><input name="code" inputmode="numeric" pattern="[0-9]{{6}}" maxlength="6" required autocomplete="one-time-code" autofocus data-auto-code>
</form>
<p class="recovery-hint">Код действует 60 минут. Запрос нового кода отменяет предыдущий.</p>
<a class="forgot-password recovery-back" href="/auth/recovery">Запросить код ещё раз</a></section>"""
    return page("Проверка кода", content, body_class="login-page")


async def password_recovery_verify(request: web.Request) -> web.Response:
    form = await request.post()
    try:
        email = WebIdentityService.normalize_email(str(form.get("email", "")))
    except ValueError:
        return error_page("Неверный или просроченный код.", status=403)
    code = str(form.get("code", "")).strip()
    if len(code) != 6 or not code.isdigit():
        return error_page("Неверный или просроченный код.", status=403)
    async with AsyncSessionLocal() as db:
        verified = await PasswordRecoveryService(db).verify_code(email, code)
    if verified is None:
        return error_page("Неверный или просроченный код.", status=403)
    _, reset_token = verified
    content = f"""<section class="login-card glass hybrid-login recovery-card"><div class="login-logo">S</div>
<h2>Установите новый пароль</h2><p>Код подтверждён. Придумайте новый пароль для дальнейшего входа.</p>
<form method="post" action="/auth/recovery/password">
<input type="hidden" name="token" value="{esc(reset_token)}">
<label>Новый пароль</label><input type="password" name="password" minlength="10" required autocomplete="new-password" autofocus>
<label>Повторите пароль</label><input type="password" name="password_confirm" minlength="10" required autocomplete="new-password">
<button type="submit">Сохранить пароль и войти</button></form>
<p class="recovery-hint">Не менее 10 символов, минимум одна буква и одна цифра. Форма действует 15 минут.</p></section>"""
    return page("Новый пароль", content, body_class="login-page")


async def password_recovery_set_password(request: web.Request) -> web.Response:
    form = await request.post()
    token = str(form.get("token", ""))
    password = str(form.get("password", ""))
    password_confirm = str(form.get("password_confirm", ""))
    if not token or password != password_confirm:
        return error_page("Пароли не совпадают. Запросите новый код и повторите попытку.", status=400)
    try:
        WebIdentityService.validate_password(password)
    except ValueError as error:
        return error_page(str(error), status=400)
    async with AsyncSessionLocal() as db:
        account = await PasswordRecoveryService(db).set_new_password(token, password)
    if account is None:
        return error_page("Ссылка смены пароля истекла. Запросите новый код.", status=403)
    return begin_two_factor_login_response(request, account.id)


async def one_c_email_login(request: web.Request) -> web.Response:
    try:
        payload = await request.json()
        email = WebIdentityService.normalize_email(str(payload.get("email", "")))
        password = str(payload.get("password", ""))
    except (ValueError, TypeError):
        return web.json_response({"ok": False, "error": "Неверный email или пароль."}, status=403)

    async with AsyncSessionLocal() as db:
        account = await db.scalar(
            select(Account).where(
                func.lower(Account.email) == email,
                Account.is_active.is_(True),
                Account.registered.is_(True),
                Account.email_verified_at.is_not(None),
            )
        )
        valid = account is not None and WebIdentityService.verify_password(
            password,
            account.password_hash,
        )
        if valid:
            account.last_login = now()
            await db.commit()
    if not valid:
        return web.json_response({"ok": False, "error": "Неверный email или пароль."}, status=403)

    two_factor_token = create_two_factor_challenge(account.id, embedded=True)
    return web.json_response(
        {
            "ok": True,
            "exchange_url": f"{WEB_PUBLIC_URL}/auth/2fa/{two_factor_token}?embedded=1c",
        }
    )


async def one_c_exchange(request: web.Request) -> web.Response:
    ticket = ONE_C_EXCHANGE_TICKETS.pop(request.match_info["ticket"], None)
    if ticket is None or ticket.expires_at <= now():
        return error_page("Билет входа истёк. Выполните вход ещё раз.", status=403)
    return begin_two_factor_login_response(request, ticket.account_id)


async def request_code(request: web.Request) -> web.Response:
    form = await request.post()
    telegram_text = str(form.get("telegram_id", "")).strip()
    if not telegram_text.isdigit():
        return error_page("Некорректный Telegram ID.")
    telegram_id = int(telegram_text)
    async with AsyncSessionLocal() as db:
        account = await db.scalar(
            select(Account).where(
                Account.telegram_id == telegram_id,
                Account.is_active.is_(True),
                Account.registered.is_(True),
            )
        )
    if account is None:
        return error_page("Активный зарегистрированный аккаунт не найден.", status=403)

    challenge_id = secrets.token_urlsafe(24)
    code = f"{secrets.randbelow(1_000_000):06d}"
    LOGIN_CHALLENGES[challenge_id] = LoginChallenge(
        account_id=account.id,
        code_hash=hashlib.sha256(code.encode()).hexdigest(),
        expires_at=now() + LOGIN_TTL,
    )
    api_url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as client:
        response = await client.post(
            api_url,
            json={
                "chat_id": telegram_id,
                "text": f"Код входа в веб-кабинет: {code}\n\nКод действует 10 минут.",
            },
        )
        if response.status >= 400:
            LOGIN_CHALLENGES.pop(challenge_id, None)
            return error_page("Не удалось отправить код через Telegram.", status=502)

    content = f"""<section class="login-card glass"><div class="login-logo">S</div>
<h2>Введите код</h2><p>Мы отправили шестизначный код в Telegram.</p>
<form method="post" action="/auth/verify" data-auto-code-form>
<input type="hidden" name="challenge" value="{esc(challenge_id)}">
<label>Код подтверждения</label><input name="code" inputmode="numeric" pattern="[0-9]{{6}}" maxlength="6" required autocomplete="one-time-code" autofocus data-auto-code>
</form></section>"""
    return page("Подтверждение", content)


async def verify_code(request: web.Request) -> web.Response:
    form = await request.post()
    challenge_id = str(form.get("challenge", ""))
    challenge = LOGIN_CHALLENGES.get(challenge_id)
    if challenge is None or challenge.expires_at <= now():
        return error_page("Код истёк. Запросите новый.", status=403)
    challenge.attempts += 1
    if challenge.attempts > 5:
        LOGIN_CHALLENGES.pop(challenge_id, None)
        return error_page("Превышено число попыток.", status=403)
    supplied = hashlib.sha256(str(form.get("code", "")).encode()).hexdigest()
    if not secrets.compare_digest(supplied, challenge.code_hash):
        return error_page("Неверный код.", status=403)

    LOGIN_CHALLENGES.pop(challenge_id, None)
    return begin_two_factor_login_response(request, challenge.account_id)


async def registration_page(request: web.Request) -> web.Response:
    token = request.query.get("token", "")
    token_hash = InviteService.make_token_hash(token)
    async with AsyncSessionLocal() as db:
        invite = await db.scalar(
            select(Invite).where(
                Invite.token_hash == token_hash,
                Invite.is_active.is_(True),
                Invite.used_at.is_(None),
                Invite.expires_at > now(),
                Invite.delivery_channel == "email",
            )
        )
    if invite is None:
        return error_page("Приглашение недействительно или уже использовано.", status=403)
    content = f'''<section class="login-card glass"><div class="login-logo">S</div>
<h2>Регистрация</h2><p>{esc(invite.full_name)}<br>{esc(invite.email)}</p>
<form method="post" action="/register"><input type="hidden" name="token" value="{esc(token)}">
<label>Пароль</label><input type="password" name="password" minlength="10" required autocomplete="new-password">
<label>Повторите пароль</label><input type="password" name="password_repeat" minlength="10" required autocomplete="new-password">
<button type="submit">Создать аккаунт</button></form></section>'''
    return page("Регистрация", content)


async def registration_submit(request: web.Request) -> web.Response:
    form = await request.post()
    token = str(form.get("token", ""))
    password = str(form.get("password", ""))
    if password != str(form.get("password_repeat", "")):
        return error_page("Пароли не совпадают.")
    try:
        password_hash = WebIdentityService.hash_password(password)
    except ValueError as error:
        return error_page(str(error))

    token_hash = InviteService.make_token_hash(token)
    async with AsyncSessionLocal() as db:
        invite = await db.scalar(
            select(Invite)
            .where(Invite.token_hash == token_hash)
            .with_for_update()
        )
        if (
            invite is None
            or not invite.is_active
            or invite.used_at is not None
            or invite.expires_at <= now()
            or invite.delivery_channel != "email"
            or not invite.email
        ):
            return error_page("Приглашение недействительно или уже использовано.", status=403)
        existing = await db.scalar(
            select(Account).where(func.lower(Account.email) == invite.email.casefold())
        )
        if existing is not None:
            return error_page("Аккаунт с таким email уже существует.", status=409)
        account = Account(
            telegram_id=None,
            email=invite.email.casefold(),
            password_hash=password_hash,
            email_verified_at=now(),
            full_name=invite.full_name,
            role=UserRole(invite.role.value),
            is_active=True,
            registered=True,
            last_login=now(),
            language="ru",
        )
        db.add(account)
        await db.flush()
        membership = AccountOrganizationalUnitMembership(
            account_id=account.id,
            organizational_unit_id=invite.organizational_unit_id,
            is_primary=True,
            is_active=True,
        )
        db.add(membership)
        invite.used_at = now()
        invite.used_by_account_id = account.id
        await db.commit()
        account_id = account.id
    return begin_two_factor_login_response(request, account_id)


def session_for(request: web.Request) -> WebSession | None:
    return WEB_SESSIONS.get(request.cookies.get(SESSION_COOKIE, ""))


def valid_csrf(request: web.Request, form) -> bool:
    session = session_for(request)
    return session is not None and secrets.compare_digest(
        str(form.get("csrf", "")),
        session.csrf_token,
    )


async def logout(request: web.Request) -> web.Response:
    token = request.cookies.get(SESSION_COOKIE, "")
    WEB_SESSIONS.pop(token, None)
    save_web_sessions()
    response = web.HTTPFound("/login")
    response.del_cookie(SESSION_COOKIE, path="/")
    return response


def employee_presence(account_id: int, fallback_login: datetime | None = None) -> dict[str, str]:
    current = now()
    snapshot = work_state_snapshot(account_id, current)
    tracking = tracking_account(account_id)
    if tracking.get("enabled") is False:
        return {"code": "disabled", "label": "Статистика рабочего времени не ведется", "login": "—", "workday_start": "—", "source": "disabled"}
    local_date = current.astimezone(DISPLAY_TIMEZONE).date().isoformat()
    manual_state = tracking.get("work_state") if tracking.get("work_state_date") == local_date else None
    if snapshot["state"] in OFFICIAL_WORK_STATES:
        manual_state = snapshot["state"]
    manual_states = set(WORK_STATE_LABELS)
    if manual_state in manual_states:
        code, label, source = manual_state, WORK_STATE_LABELS[manual_state], "manual"
        agent_seen = None
    else:
        agent_seen = None
    try:
        agent_seen = datetime.fromisoformat(str(tracking.get("agent_last_seen_at", "")))
    except ValueError:
        pass
    if manual_state not in manual_states and agent_seen and current - agent_seen <= PRESENCE_ONLINE_TTL:
        if tracking.get("agent_locked"):
            code, label = "away", "Не на месте"
        elif int(tracking.get("agent_idle_seconds", 0)) <= int(PRESENCE_ACTIVE_TTL.total_seconds()):
            code, label = "working", "Работает"
        else:
            code, label = "idle", "Бездействует"
        source = "agent"
    elif manual_state not in manual_states:
        source = "browser"
    sessions = [
        item for item in WEB_SESSIONS.values()
        if item.account_id == account_id and item.expires_at > current
    ]
    login_at = max((item.login_at for item in sessions), default=LAST_LOGIN_TIMES.get(account_id, fallback_login))
    online = [item for item in sessions if current - item.last_seen_at <= PRESENCE_ONLINE_TTL]
    if source == "browser":
        if not online:
            code, label = "away", "Не на месте"
        elif any(current - item.last_activity_at <= PRESENCE_ACTIVE_TTL for item in online):
            code, label = "working", "Работает"
        else:
            code, label = "idle", "Бездействует"
    workday_value = WORK_TRACKING.setdefault("workdays", {}).get(f"{account_id}:{local_date}")
    try:
        workday_start = datetime.fromisoformat(workday_value).astimezone(DISPLAY_TIMEZONE).strftime("%H:%M:%S")
    except (TypeError, ValueError):
        workday_start = "—"
    return {
        "code": code,
        "label": label,
        "login": login_at.astimezone(DISPLAY_TIMEZONE).strftime("%d.%m.%Y %H:%M:%S") if login_at else "Никогда",
        "workday_start": workday_start,
        "source": source,
    }


async def agent_heartbeat(request: web.Request) -> web.Response:
    authorization = request.headers.get("Authorization", "")
    token = authorization.removeprefix("Bearer ").strip()
    match = None
    for account_id, item in WORK_TRACKING.setdefault("accounts", {}).items():
        if token and secrets.compare_digest(str(item.get("token", "")), token):
            match = (account_id, item); break
    if match is None:
        return web.json_response({"error": "Неверный токен агента."}, status=401)
    account_id, item = match
    if item.get("enabled") is False:
        return web.json_response({"tracking": False}, status=403)
    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError):
        return web.json_response({"error": "Некорректные данные."}, status=400)
    heartbeat_at = now()
    idle_seconds = max(0, min(int(payload.get("idle_seconds", 0)), 86400))
    locked = bool(payload.get("locked"))
    previous_seen = None
    try:
        previous_seen = datetime.fromisoformat(str(item.get("agent_last_seen_at", "")))
    except ValueError:
        pass
    item.update({
        "agent_last_seen_at": heartbeat_at.isoformat(),
        "agent_idle_seconds": idle_seconds,
        "agent_locked": locked,
        "agent_platform": str(payload.get("platform", ""))[:24],
        "agent_version": str(payload.get("version", ""))[:32],
    })
    if not locked and idle_seconds <= int(PRESENCE_ACTIVE_TTL.total_seconds()):
        item["agent_last_active_at"] = (heartbeat_at - timedelta(seconds=idle_seconds)).isoformat()
        if active_official_absence(int(account_id), heartbeat_at) is not None and previous_seen is not None:
            elapsed = max(0, min(60, int((heartbeat_at - previous_seen).total_seconds())))
            day_key = heartbeat_at.astimezone(DISPLAY_TIMEZONE).date().isoformat()
            overtime = item.setdefault("official_overtime", {})
            overtime[day_key] = int(overtime.get(day_key, 0)) + elapsed
    save_work_tracking()
    return web.json_response({"tracking": True, **work_state_snapshot(int(account_id), heartbeat_at)})


@authenticated
async def web_work_state_update(request: web.Request, account: Account) -> web.Response:
    if request.headers.get("X-Requested-With") != "SupportBot":
        return web.json_response({"error": "Проверка безопасности не пройдена."}, status=403)
    if tracking_account(account.id).get("enabled") is False:
        return web.json_response({"error": "Статистика рабочего времени отключена."}, status=403)
    try:
        payload = await request.json()
        state = str(payload.get("state", ""))
        reason = str(payload.get("reason", ""))
        if state == "other" and not reason.strip():
            raise ValueError("Укажите причину отсутствия.")
        result = set_work_state(account.id, state, "web", reason=reason, starts_at=str(payload.get("starts_at", "")), ends_at=str(payload.get("ends_at", "")))
    except (json.JSONDecodeError, ValueError) as error:
        return web.json_response({"error": str(error)}, status=400)
    return web.json_response(result)


@authenticated
async def web_work_state_current(request: web.Request, account: Account) -> web.Response:
    if tracking_account(account.id).get("enabled") is False:
        return web.json_response({"state": "disabled", "label": "Статистика рабочего времени не ведется", "reminder": "", "overtime_seconds": 0})
    return web.json_response(work_state_snapshot(account.id))


async def agent_work_state_update(request: web.Request) -> web.Response:
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    account_id = None
    for value, item in WORK_TRACKING.setdefault("accounts", {}).items():
        if token and secrets.compare_digest(str(item.get("token", "")), token):
            if item.get("enabled") is False:
                return web.json_response({"error": "Статистика рабочего времени отключена."}, status=403)
            account_id = int(value)
            break
    if account_id is None:
        return web.json_response({"error": "Неверный токен агента."}, status=401)
    try:
        payload = await request.json()
        result = set_work_state(account_id, str(payload.get("state", "")), "agent", reason=str(payload.get("reason", "")), starts_at=str(payload.get("starts_at", "")), ends_at=str(payload.get("ends_at", "")))
    except (json.JSONDecodeError, ValueError) as error:
        return web.json_response({"error": str(error)}, status=400)
    return web.json_response(result)


def can_manage_work_tracking(account: Account) -> bool:
    return account.role in {UserRole.ADMIN, UserRole.COORDINATOR}


@authenticated
async def employee_tracking_update(request: web.Request, account: Account) -> web.Response:
    if not can_manage_work_tracking(account):
        return error_page("Недостаточно прав.", status=403, account=account)
    form = await request.post()
    if not valid_csrf(request, form):
        return error_page("Проверка безопасности не пройдена.", status=403, account=account)
    employee_id = int(request.match_info["id"])
    item = tracking_account(employee_id)
    item["enabled"] = str(form.get("enabled", "")) == "1"
    if item["enabled"] is False:
        for key in list(item):
            if key.startswith("agent_"):
                item.pop(key, None)
    save_work_tracking()
    raise web.HTTPFound(f"/employees/{employee_id}")


@authenticated
async def employee_schedule_update(request: web.Request, account: Account) -> web.Response:
    if not can_manage_work_tracking(account):
        return error_page("Недостаточно прав.", status=403, account=account)
    form = await request.post()
    if not valid_csrf(request, form):
        return error_page("Проверка безопасности не пройдена.", status=403, account=account)
    employee_id = int(request.match_info["id"])
    start = str(form.get("start", "")).strip()
    end = str(form.get("end", "")).strip()
    if re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", start) is None or re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", end) is None:
        return error_page("Укажите корректное время начала и окончания работы.", account=account)
    weekdays = sorted({int(value) for value in form.getall("weekday", []) if str(value).isdigit() and 0 <= int(value) <= 6})
    if not weekdays:
        return error_page("Выберите хотя бы один рабочий день.", account=account)
    tracking_account(employee_id)["schedule"] = {"start": start, "end": end, "weekdays": weekdays, "timezone": "Europe/Kaliningrad"}
    save_work_tracking()
    raise web.HTTPFound(f"/employees/{employee_id}")


async def presence_heartbeat(request: web.Request) -> web.Response:
    session = session_for(request)
    if session is None:
        return web.json_response({"error": "Требуется вход."}, status=401)
    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError):
        payload = {}
    timestamp = now()
    session.last_seen_at = timestamp
    if bool(payload.get("active")):
        session.last_activity_at = timestamp
    save_web_sessions()
    return web.json_response(employee_presence(session.account_id))


@authenticated
async def presence_statuses(request: web.Request, account: Account) -> web.Response:
    if not await can(account, Permission.EMPLOYEE_VIEW):
        return web.json_response({"error": "Недостаточно прав."}, status=403)
    ids = {int(value) for value in request.query.get("ids", "").split(",") if value.isdigit()}
    ids = set(list(ids)[:100])
    async with AsyncSessionLocal() as db:
        rows = list(await db.scalars(select(Account).where(Account.id.in_(ids)))) if ids else []
    return web.json_response({str(item.id): employee_presence(item.id, item.last_login) for item in rows})


@authenticated
async def dashboard(request: web.Request, account: Account) -> web.Response:
    sections = [
        ("organizations", "Организации", Permission.ORGANIZATION_VIEW),
        ("holdings", "Холдинги", Permission.HOLDING_VIEW),
        ("employees", "Сотрудники", Permission.EMPLOYEE_VIEW),
        ("tickets", "Тикеты", Permission.TICKET_VIEW),
        ("reports", "Отчёты", Permission.REPORT_VIEW),
        ("access", "Доступы", Permission.ROLE_ASSIGN),
        ("profile", "Профиль", None),
        ("language", "Language", None),
    ]
    allowed = []
    for path, label, permission in sections:
        if permission is None or await can(account, permission):
            allowed.append(
                f'<a class="launch-app" href="/{path}"><span class="app-icon">'
                f'{icon_image(path)}</span><span>{label}</span></a>'
            )
    return page(
        "Главная",
        f'<section class="launch-grid">{"".join(allowed)}</section>',
        account=account,
    )


async def application_version(request: web.Request) -> web.Response:
    return web.json_response({"version": APP_BUILD})


@authenticated
async def organizations(request: web.Request, account: Account) -> web.Response:
    if not await can(account, Permission.ORGANIZATION_VIEW):
        return error_page("Недостаточно прав.", status=403, account=account)
    query = request.query.get("q", "").strip()

    search = search_form(
        "/organizations",
        query,
        "ИНН или часть наименования",
    ).replace('class="search glass"', 'class="search glass search-wide"')
    create_action = ""
    if await can(account, Permission.ORGANIZATION_MANAGE):
        create_action = (
            '<div class="action-bar organizations-action-bar">'
            '<a class="button" href="/organizations/create">➕ Новая организация</a></div>'
        )
    if not query:
        return page(
            "Организации",
            create_action
            + search
            + '<section class="empty glass">Введите ИНН или часть '
            "наименования организации.</section>",
            account=account,
            active="organizations",
        )
    if len(query) < 2:
        return page(
            "Организации",
            create_action
            + search
            + '<section class="empty glass">Запрос должен содержать '
            "не менее двух символов.</section>",
            account=account,
            active="organizations",
        )

    async with AsyncSessionLocal() as db:
        values = await OrganizationAccessService(db).list_visible_organizations(account)
    digits = "".join(filter(str.isdigit, query))
    values = [
        item
        for item in values
        if query.casefold() in item.name.casefold()
        or (digits and digits in (item.inn or ""))
    ][:8]
    items = [
        f'<a class="data-card glass" href="/organizations/{item.id}"><div class="card-icon">🏢</div>'
        f'<div><h3>{esc(item.name)}</h3><p>ИНН {esc(item.inn or "не указан")} · {"Активна" if item.is_active else "Архив"}</p></div></a>'
        for item in values
    ]
    return page(
        "Организации",
        create_action + search + cards(items, "Совпадений среди доступных организаций нет"),
        account=account,
        active="organizations",
    )


@authenticated
async def organization_create_page(request: web.Request, account: Account) -> web.Response:
    if not await can(account, Permission.ORGANIZATION_MANAGE):
        return error_page("Недостаточно прав.", status=403, account=account)
    async with AsyncSessionLocal() as db:
        parents = await OrganizationAccessService(db).list_visible_organizations(
            account, active=True
        )
    parent_options = '<option value="">Без родительской организации</option>' + "".join(
        f'<option value="{item.id}">{esc(item.name)}</option>' for item in parents
    )
    type_options = "".join(
        f'<option value="{item.value}">{esc(organization_type_label(item))}</option>'
        for item in (
            OrganizationType.CUSTOMER,
            OrganizationType.SUPPORT_PROVIDER,
            OrganizationType.PARTNER,
        )
    )
    session = session_for(request)
    content = f'''<section class="panel glass form-panel"><h2>Новая организация</h2>
<form method="post" action="/organizations/create"><input type="hidden" name="csrf" value="{esc(session.csrf_token)}">
<div class="form-grid"><label>Наименование<input name="name" required minlength="2" maxlength="255" autofocus></label>
<label>Тип организации<select name="organization_type" required>{type_options}</select></label>
<label>Родительская организация<select name="parent_id">{parent_options}</select></label></div>
<div class="action-bar"><button class="button" type="submit">Создать организацию</button><a class="button secondary-link" href="/organizations">Отмена</a></div>
</form></section>'''
    return page("Новая организация", content, account=account, active="organizations")


@authenticated
async def organization_create_submit(request: web.Request, account: Account) -> web.Response:
    if not await can(account, Permission.ORGANIZATION_MANAGE):
        return error_page("Недостаточно прав.", status=403, account=account)
    form = await request.post()
    if not valid_csrf(request, form):
        return error_page("Проверка безопасности не пройдена.", status=403, account=account)
    parent_value = str(form.get("parent_id", "")).strip()
    try:
        parent_id = int(parent_value) if parent_value else None
        organization_type = OrganizationType(str(form.get("organization_type", "")))
    except (TypeError, ValueError):
        return error_page("Неверно указан тип или родительская организация.", account=account)
    if organization_type == OrganizationType.PLATFORM:
        return error_page("Нельзя создать платформенную организацию через эту форму.", status=403, account=account)
    async with AsyncSessionLocal() as db:
        if parent_id is not None:
            access = OrganizationAccessService(db)
            if not await access.can_access_organization(account, parent_id):
                return error_page("Родительская организация недоступна.", status=403, account=account)
        try:
            organization = await OrganizationService(db).create_organization(
                name=str(form.get("name", "")),
                organization_type=organization_type,
                parent_id=parent_id,
                actor_account_id=account.id,
            )
        except ValueError as error:
            return error_page(str(error), account=account)
    raise web.HTTPFound(f"/organizations/{organization.id}")


@authenticated
async def organization_card(request: web.Request, account: Account) -> web.Response:
    organization_id = int(request.match_info["id"])
    async with AsyncSessionLocal() as db:
        access = OrganizationAccessService(db)
        if not await access.can_access_organization(account, organization_id):
            return error_page("Организация недоступна.", status=403, account=account)
        organization = await OrganizationService(db).get_organization(
            organization_id,
            include_children=True,
        )
        holdings = list(await db.scalars(select(Holding).where(Holding.organization_id == organization_id).order_by(Holding.name)))
        units = list(await db.scalars(select(OrganizationalUnit).where(OrganizationalUnit.organization_id == organization_id).order_by(OrganizationalUnit.name)))
        manage_allowed = await AuthorizationService.can_async(
            account,
            Permission.ORGANIZATION_MANAGE,
            scope=AccessScope.organization(organization_id),
            session=db,
        )
        audit_allowed = await AuthorizationService.can_async(
            account,
            Permission.ORGANIZATION_AUDIT_VIEW,
            scope=AccessScope.organization(organization_id),
            session=db,
        )
    session = session_for(request)
    csrf = esc(session.csrf_token)
    action_items = [
        '<a class="org-action" href="#units">🏗 <span>Подразделения</span></a>',
        f'<a class="org-action" href="/organizations/{organization_id}/structure">🗺 <span>Структура компании</span></a>',
    ]
    if manage_allowed:
        action_items.extend(
            [
                f'<a class="org-action" href="/organizations/{organization_id}/email-domains">✉ <span>Почтовые домены</span></a>',
                f'<a class="org-action" href="/organizations/{organization_id}/registry">🏢 <span>Заполнить по ИНН</span></a>',
                f'<form method="post" action="/organizations/{organization_id}/registry/update"><input type="hidden" name="csrf" value="{csrf}"><button class="org-action" type="submit">🔄 <span>Обновить из реестра</span></button></form>',
                f'<a class="org-action" href="/organizations/{organization_id}/rename">✏️ <span>Переименовать</span></a>',
                f'<form method="post" action="/organizations/{organization_id}/lifecycle"><input type="hidden" name="csrf" value="{csrf}"><button class="org-action" type="submit">{"📦" if organization.is_active else "✅"} <span>{"Архивировать" if organization.is_active else "Восстановить"}</span></button></form>',
            ]
        )
    if audit_allowed:
        action_items.append(
            f'<a class="org-action" href="/organizations/{organization_id}/audit">📜 <span>История организации</span></a>'
        )
    action_items.extend(
        [
            '<a class="org-action navigation" href="/organizations">⬅️ <span>Поиск организаций</span></a>',
            '<a class="org-action navigation" href="/">⌂ <span>На главную</span></a>',
        ]
    )
    synchronized = (
        organization.last_registry_sync_at.strftime("%d.%m.%Y %H:%M")
        if organization.last_registry_sync_at
        else "ещё не выполнялась"
    )
    allowed_domains = organization_email_domains(organization)
    allowed_domains_label = ", ".join("@" + item for item in allowed_domains) or "не настроены"
    content = f'''<section class="organization-layout"><article class="organization-card panel glass">
<div class="organization-heading"><div class="hero-icon">🏢</div><div><span class="status-pill">{"активна" if organization.is_active else "отключена"}</span><h2>{esc(organization.name)}</h2><p>{esc(organization_type_label(organization.organization_type))}</p></div></div>
<div class="card-section"><h3>Организация</h3><dl><dt>ID</dt><dd>{esc(organization.external_id)}</dd><dt>Название</dt><dd>{esc(organization.name)}</dd><dt>Тип</dt><dd>{esc(organization_type_label(organization.organization_type))}</dd><dt>Статус</dt><dd>{"активна" if organization.is_active else "отключена"}</dd><dt>Родитель</dt><dd>{esc(organization.parent.name if organization.parent else "нет")}</dd></dl></div>
<div class="card-section"><h3>Юридические данные</h3><dl><dt>Название</dt><dd>{esc(organization.legal_name or "не заполнено")}</dd><dt>ИНН</dt><dd>{esc(organization.inn or "не заполнен")}</dd><dt>КПП</dt><dd>{esc(organization.kpp or "не заполнен")}</dd><dt>ОГРН</dt><dd>{esc(organization.ogrn or "не заполнен")}</dd><dt>Юр. статус</dt><dd>{esc(organization.legal_status or "не заполнен")}</dd><dt>Синхронизация</dt><dd>{esc(synchronized)}</dd></dl></div>
<div class="card-section"><h3>Правила email</h3><dl><dt>Разрешённые домены</dt><dd>{esc(allowed_domains_label)}</dd></dl></div>
<div class="organization-counters"><span>Дочерних организаций <b>{len(organization.children)}</b></span><span>Холдингов <b>{len(holdings)}</b></span></div></article>
<aside class="organization-actions glass"><h3>Действия</h3>{''.join(action_items)}</aside></section>
<section id="units" class="panel glass content-section"><h2>Подразделения</h2>{''.join(f'<div class="list-row">🏗️ {esc(unit.name)}</div>' for unit in units) or '<p>Нет подразделений</p>'}</section>
<article class="panel glass content-section"><h2>Холдинги</h2>{''.join(f'<a class="list-row" href="/holdings/{holding.id}">🏛️ {esc(holding.name)}</a>' for holding in holdings) or '<p>Нет холдингов</p>'}</article>'''
    return page("Карточка организации", content, account=account, active="organizations")


@authenticated
async def organization_email_domains_page(request: web.Request, account: Account) -> web.Response:
    organization_id = int(request.match_info["id"])
    db = await require_organization_action(
        account, organization_id, Permission.ORGANIZATION_MANAGE
    )
    if db is None:
        return error_page("Недостаточно прав.", status=403, account=account)
    async with db:
        organization = await OrganizationService(db).require_organization(organization_id)
    session = session_for(request)
    value = "\n".join(organization_email_domains(organization))
    content = f'''<section class="panel glass form-panel"><h2>Разрешённые почтовые домены</h2>
<p>Укажите домены, которые сотрудники этой организации могут использовать. Один домен на строку, например <b>yandex.ru</b>. Пока список пуст, смена email сотрудниками запрещена.</p>
<form method="post" action="/organizations/{organization_id}/email-domains"><input type="hidden" name="csrf" value="{esc(session.csrf_token)}">
<label>Домены<textarea name="domains" rows="8" maxlength="4000" placeholder="company.ru&#10;subsidiary.ru">{esc(value)}</textarea></label>
<div class="action-bar"><button class="button" type="submit">Сохранить правила</button><a class="button secondary-link" href="/organizations/{organization_id}">Отмена</a></div>
</form></section>'''
    return page("Почтовые домены", content, account=account, active="organizations")


@authenticated
async def organization_email_domains_update(request: web.Request, account: Account) -> web.Response:
    organization_id = int(request.match_info["id"])
    form = await request.post()
    if not valid_csrf(request, form):
        return error_page("Проверка безопасности не пройдена.", status=403, account=account)
    try:
        domains = normalize_email_domains(str(form.get("domains", "")))
    except ValueError as error:
        return error_page(str(error), account=account)
    db = await require_organization_action(
        account, organization_id, Permission.ORGANIZATION_MANAGE
    )
    if db is None:
        return error_page("Недостаточно прав.", status=403, account=account)
    async with db:
        organization = await OrganizationService(db).require_organization(organization_id)
        previous = organization_email_domains(organization)
        organization.allowed_email_domains = "\n".join(domains) or None
        await OrganizationAuditService(db).create_event(
            organization_id=organization_id,
            event_type="email_domains_updated",
            title="Изменены правила корпоративной почты",
            source="web",
            actor_account_id=account.id,
            details=(
                "Разрешённые домены: " + (", ".join(domains) if domains else "список очищен")
            ),
            payload={"before": previous, "after": domains},
            commit=False,
        )
        await db.commit()
    raise web.HTTPFound(f"/organizations/{organization_id}")


async def require_organization_action(
    account: Account,
    organization_id: int,
    permission: Permission,
):
    db = AsyncSessionLocal()
    access = OrganizationAccessService(db)
    if not await access.can_access_organization(account, organization_id):
        await db.close()
        return None
    allowed = await AuthorizationService.can_async(
        account,
        permission,
        scope=AccessScope.organization(organization_id),
        session=db,
    )
    if not allowed:
        await db.close()
        return None
    return db


@authenticated
async def organization_rename_page(request: web.Request, account: Account) -> web.Response:
    organization_id = int(request.match_info["id"])
    db = await require_organization_action(
        account,
        organization_id,
        Permission.ORGANIZATION_MANAGE,
    )
    if db is None:
        return error_page("Недостаточно прав.", status=403, account=account)
    async with db:
        organization = await OrganizationService(db).require_organization(organization_id)
    session = session_for(request)
    content = f'''<section class="panel glass form-panel"><h2>Переименование</h2>
<form method="post" action="/organizations/{organization_id}/rename"><input type="hidden" name="csrf" value="{esc(session.csrf_token)}">
<div class="form-grid"><label>Новое название<input name="name" value="{esc(organization.name)}" required minlength="2" maxlength="255"></label></div>
<div class="action-bar"><button class="button" type="submit">Сохранить</button><a class="button secondary-link" href="/organizations/{organization_id}">Отмена</a></div></form></section>'''
    return page("Переименовать организацию", content, account=account, active="organizations")


@authenticated
async def organization_rename_update(request: web.Request, account: Account) -> web.Response:
    organization_id = int(request.match_info["id"])
    form = await request.post()
    if not valid_csrf(request, form):
        return error_page("Проверка безопасности не пройдена.", status=403, account=account)
    db = await require_organization_action(account, organization_id, Permission.ORGANIZATION_MANAGE)
    if db is None:
        return error_page("Недостаточно прав.", status=403, account=account)
    async with db:
        try:
            await OrganizationService(db).rename_organization(
                organization_id,
                str(form.get("name", "")),
                actor_account_id=account.id,
            )
        except ValueError as error:
            return error_page(str(error), account=account)
    raise web.HTTPFound(f"/organizations/{organization_id}")


@authenticated
async def organization_lifecycle(request: web.Request, account: Account) -> web.Response:
    organization_id = int(request.match_info["id"])
    form = await request.post()
    if not valid_csrf(request, form):
        return error_page("Проверка безопасности не пройдена.", status=403, account=account)
    db = await require_organization_action(account, organization_id, Permission.ORGANIZATION_MANAGE)
    if db is None:
        return error_page("Недостаточно прав.", status=403, account=account)
    async with db:
        service = OrganizationService(db)
        organization = await service.require_organization(organization_id)
        await service.set_organization_active(
            organization_id,
            not organization.is_active,
            actor_account_id=account.id,
        )
    raise web.HTTPFound(f"/organizations/{organization_id}")


@authenticated
async def organization_registry_page(request: web.Request, account: Account) -> web.Response:
    organization_id = int(request.match_info["id"])
    db = await require_organization_action(account, organization_id, Permission.ORGANIZATION_MANAGE)
    if db is None:
        return error_page("Недостаточно прав.", status=403, account=account)
    async with db:
        organization = await OrganizationService(db).require_organization(organization_id)
    session = session_for(request)
    content = f'''<section class="panel glass form-panel"><h2>Заполнение по ИНН</h2><p>Юридические данные будут загружены из DaData.</p>
<form method="post" action="/organizations/{organization_id}/registry"><input type="hidden" name="csrf" value="{esc(session.csrf_token)}">
<div class="form-grid"><label>ИНН<input name="inn" value="{esc(organization.inn or '')}" inputmode="numeric" required minlength="10" maxlength="12"></label></div>
<div class="action-bar"><button class="button" type="submit">Загрузить данные</button><a class="button secondary-link" href="/organizations/{organization_id}">Отмена</a></div></form></section>'''
    return page("Юридические данные", content, account=account, active="organizations")


async def sync_organization_from_request(
    request: web.Request,
    account: Account,
    *,
    use_form_inn: bool,
) -> web.Response:
    organization_id = int(request.match_info["id"])
    form = await request.post()
    if not valid_csrf(request, form):
        return error_page("Проверка безопасности не пройдена.", status=403, account=account)
    db = await require_organization_action(account, organization_id, Permission.ORGANIZATION_MANAGE)
    if db is None:
        return error_page("Недостаточно прав.", status=403, account=account)
    async with db:
        try:
            await OrganizationRegistryService(db).sync_organization(
                organization_id,
                inn=str(form.get("inn", "")) if use_form_inn else None,
                actor_account_id=account.id,
            )
        except ValueError as error:
            return error_page(str(error), account=account)
    raise web.HTTPFound(f"/organizations/{organization_id}")


@authenticated
async def organization_registry_fill(request: web.Request, account: Account) -> web.Response:
    return await sync_organization_from_request(request, account, use_form_inn=True)


@authenticated
async def organization_registry_update(request: web.Request, account: Account) -> web.Response:
    return await sync_organization_from_request(request, account, use_form_inn=False)


@authenticated
async def organization_audit_page(request: web.Request, account: Account) -> web.Response:
    organization_id = int(request.match_info["id"])
    db = await require_organization_action(account, organization_id, Permission.ORGANIZATION_AUDIT_VIEW)
    if db is None:
        return error_page("Недостаточно прав.", status=403, account=account)
    async with db:
        organization = await OrganizationService(db).require_organization(organization_id)
        events = await OrganizationAuditService(db).list_organization_events(organization_id, limit=30)
    rows = "".join(
        f'<article class="message glass"><b>{esc(event.title)}</b><time>{event.created_at:%d.%m.%Y %H:%M}</time><p>{esc(event.details or event.event_type)}</p></article>'
        for event in events
    )
    content = f'<div class="action-bar"><a class="button secondary-link" href="/organizations/{organization_id}">К карточке</a></div><section class="message-list">{rows or "<p>Изменений пока нет.</p>"}</section>'
    return page(f"История · {organization.name}", content, account=account, active="organizations")


@authenticated
async def organization_structure(request: web.Request, account: Account) -> web.Response:
    organization_id = int(request.match_info["id"])
    db = await require_organization_action(account, organization_id, Permission.ORGANIZATION_VIEW)
    if db is None:
        return error_page("Недостаточно прав.", status=403, account=account)
    async with db:
        content, filename = await CompanyStructurePdfService(db).generate(organization_id)
    return web.Response(
        body=content,
        content_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
            "Cache-Control": "no-store, max-age=0",
        },
    )


@authenticated
async def holdings_page(request: web.Request, account: Account) -> web.Response:
    if not await can(account, Permission.HOLDING_VIEW):
        return error_page("Недостаточно прав.", status=403, account=account)
    query = request.query.get("q", "").strip().casefold()
    async with AsyncSessionLocal() as db:
        values = await HoldingAccessService(db).list_visible_holdings(account)
    if query:
        values = [item for item in values if query in item.name.casefold() or query in item.organization.name.casefold()]
    items = [f'<a class="data-card glass" href="/holdings/{item.id}"><div class="card-icon">🏛️</div><div><h3>{esc(item.name)}</h3><p>{esc(item.organization.name)} · {"Активен" if item.is_active else "Архив"}</p></div></a>' for item in values]
    create_action = ""
    if await can(account, Permission.HOLDING_MANAGE):
        create_action = '<a class="button" href="/holdings/create">➕ Создать холдинг</a>'
    navigation = (
        f'<div class="action-bar"><a class="button secondary-link" href="/holdings">🔎 Найти холдинг</a>{create_action}'
        '<a class="button secondary-link" href="/">⬅️ На главную</a></div>'
    )
    return page("Холдинги", navigation + search_form("/holdings", request.query.get("q", ""), "Название холдинга или организации") + cards(items), account=account, active="holdings")


@authenticated
async def holding_create_page(request: web.Request, account: Account) -> web.Response:
    if not await can(account, Permission.HOLDING_MANAGE):
        return error_page("Недостаточно прав.", status=403, account=account)
    query = request.query.get("q", "").strip()
    organization_id_text = request.query.get("organization_id", "")
    session = session_for(request)
    if organization_id_text.isdigit():
        organization_id = int(organization_id_text)
        async with AsyncSessionLocal() as db:
            access = OrganizationAccessService(db)
            allowed = await access.can_access_organization(account, organization_id)
            allowed = allowed and await AuthorizationService.can_async(
                account,
                Permission.HOLDING_MANAGE,
                scope=AccessScope.organization(organization_id),
                session=db,
            )
            organization = await db.get(Organization, organization_id) if allowed else None
        if organization is None:
            return error_page("Организация недоступна.", status=403, account=account)
        content = f'''<section class="panel glass form-panel"><h2>Новый холдинг</h2><p>Организация: <b>{esc(organization.name)}</b></p>
<form method="post" action="/holdings/create"><input type="hidden" name="csrf" value="{esc(session.csrf_token)}"><input type="hidden" name="organization_id" value="{organization.id}">
<div class="form-grid"><label>Название холдинга<input name="name" required minlength="2" maxlength="255" autofocus></label></div>
<div class="action-bar"><button class="button" type="submit">Создать</button><a class="button secondary-link" href="/holdings/create">Выбрать другую организацию</a></div></form></section>'''
        return page("Создать холдинг", content, account=account, active="holdings")
    search = search_form("/holdings/create", query, "ИНН или часть наименования организации")
    if len(query) < 2:
        prompt = "Введите ИНН или часть наименования организации."
        if query:
            prompt = "Запрос должен содержать не менее двух символов."
        return page("Создать холдинг", search + f'<section class="empty glass">{prompt}</section>', account=account, active="holdings")
    async with AsyncSessionLocal() as db:
        organizations = await OrganizationAccessService(db).list_visible_organizations(account, active=True)
    digits = "".join(filter(str.isdigit, query))
    matches = [
        item
        for item in organizations
        if query.casefold() in item.name.casefold()
        or (digits and digits in (item.inn or ""))
    ][:8]
    results = [
        f'<a class="data-card glass" href="/holdings/create?organization_id={item.id}"><div class="card-icon">🏢</div><div><h3>{esc(item.name)}</h3><p>ИНН {esc(item.inn or "не указан")}</p></div></a>'
        for item in matches
    ]
    return page("Создать холдинг", search + cards(results, "Доступные организации не найдены"), account=account, active="holdings")


@authenticated
async def holding_create_submit(request: web.Request, account: Account) -> web.Response:
    form = await request.post()
    if not valid_csrf(request, form):
        return error_page("Проверка безопасности не пройдена.", status=403, account=account)
    try:
        organization_id = int(str(form.get("organization_id", "")))
    except ValueError:
        return error_page("Организация не выбрана.", account=account)
    async with AsyncSessionLocal() as db:
        access = OrganizationAccessService(db)
        allowed = await access.can_access_organization(account, organization_id)
        allowed = allowed and await AuthorizationService.can_async(
            account,
            Permission.HOLDING_MANAGE,
            scope=AccessScope.organization(organization_id),
            session=db,
        )
        if not allowed:
            return error_page("Недостаточно прав.", status=403, account=account)
        try:
            holding = await HoldingService(db).create_holding(
                organization_id=organization_id,
                name=str(form.get("name", "")),
                actor_account_id=account.id,
            )
        except ValueError as error:
            return error_page(str(error), account=account)
    raise web.HTTPFound(f"/holdings/{holding.id}")


@authenticated
async def holding_card(request: web.Request, account: Account) -> web.Response:
    holding_id = int(request.match_info["id"])
    async with AsyncSessionLocal() as db:
        access = HoldingAccessService(db)
        if not await access.can_access_holding(account, holding_id):
            return error_page("Холдинг недоступен.", status=403, account=account)
        item = await db.scalar(select(Holding).where(Holding.id == holding_id).options(selectinload(Holding.organization)))
        manage_allowed = await AuthorizationService.can_async(
            account,
            Permission.HOLDING_MANAGE,
            scope=AccessScope.holding(holding_id),
            session=db,
        )
        audit_allowed = await AuthorizationService.can_async(
            account,
            Permission.HOLDING_AUDIT_VIEW,
            scope=AccessScope.holding(holding_id),
            session=db,
        )
    session = session_for(request)
    actions = [
        f'<a class="org-action" href="/holdings/{holding_id}/companies">🏢 <span>Компании холдинга</span></a>',
        f'<a class="org-action" href="/holdings/{holding_id}/admins">👤 <span>Администраторы холдинга</span></a>',
    ]
    if audit_allowed:
        actions.append(f'<a class="org-action" href="/holdings/{holding_id}/audit">📜 <span>История холдинга</span></a>')
    if manage_allowed:
        actions.extend(
            [
                f'<a class="org-action" href="/holdings/{holding_id}/rename">✏️ <span>Переименовать холдинг</span></a>',
                f'<form method="post" action="/holdings/{holding_id}/lifecycle"><input type="hidden" name="csrf" value="{esc(session.csrf_token)}"><button class="org-action" type="submit">{"📦" if item.is_active else "✅"} <span>{"Архивировать холдинг" if item.is_active else "Восстановить холдинг"}</span></button></form>',
            ]
        )
    actions.extend(
        [
            '<a class="org-action navigation" href="/holdings">⬅️ <span>Каталог холдингов</span></a>',
            '<a class="org-action navigation" href="/">⌂ <span>На главную</span></a>',
        ]
    )
    content = f'''<section class="organization-layout"><article class="panel glass"><div class="organization-heading"><div class="hero-icon">🏛️</div><div><span class="status-pill">{"активен" if item.is_active else "в архиве"}</span><h2>{esc(item.name)}</h2><p>Холдинг</p></div></div>
<div class="card-section"><h3>Холдинг</h3><dl><dt>Название</dt><dd>{esc(item.name)}</dd><dt>Организация</dt><dd><a href="/organizations/{item.organization_id}">{esc(item.organization.name)}</a></dd><dt>Статус</dt><dd>{"активен" if item.is_active else "в архиве"}</dd><dt>Создан</dt><dd>{esc(item.created_at.strftime("%d.%m.%Y"))}</dd></dl></div></article>
<aside class="organization-actions glass"><h3>Действия</h3>{''.join(actions)}</aside></section>'''
    return page("Карточка холдинга", content, account=account, active="holdings")


async def require_holding_action(account: Account, holding_id: int, permission: Permission):
    db = AsyncSessionLocal()
    if not await HoldingAccessService(db).can_access_holding(account, holding_id):
        await db.close()
        return None
    allowed = await AuthorizationService.can_async(
        account,
        permission,
        scope=AccessScope.holding(holding_id),
        session=db,
    )
    if not allowed:
        await db.close()
        return None
    return db


@authenticated
async def holding_rename_page(request: web.Request, account: Account) -> web.Response:
    holding_id = int(request.match_info["id"])
    db = await require_holding_action(account, holding_id, Permission.HOLDING_MANAGE)
    if db is None:
        return error_page("Недостаточно прав.", status=403, account=account)
    async with db:
        holding = await HoldingService(db).require_holding(holding_id)
    session = session_for(request)
    content = f'''<section class="panel glass form-panel"><h2>Переименование холдинга</h2><form method="post" action="/holdings/{holding_id}/rename"><input type="hidden" name="csrf" value="{esc(session.csrf_token)}"><div class="form-grid"><label>Новое название<input name="name" value="{esc(holding.name)}" required minlength="2" maxlength="255"></label></div><div class="action-bar"><button class="button" type="submit">Сохранить</button><a class="button secondary-link" href="/holdings/{holding_id}">Отмена</a></div></form></section>'''
    return page("Переименовать холдинг", content, account=account, active="holdings")


@authenticated
async def holding_rename_update(request: web.Request, account: Account) -> web.Response:
    holding_id = int(request.match_info["id"])
    form = await request.post()
    if not valid_csrf(request, form):
        return error_page("Проверка безопасности не пройдена.", status=403, account=account)
    db = await require_holding_action(account, holding_id, Permission.HOLDING_MANAGE)
    if db is None:
        return error_page("Недостаточно прав.", status=403, account=account)
    async with db:
        try:
            await HoldingService(db).rename_holding(
                holding_id,
                str(form.get("name", "")),
                actor_account_id=account.id,
            )
        except ValueError as error:
            return error_page(str(error), account=account)
    raise web.HTTPFound(f"/holdings/{holding_id}")


@authenticated
async def holding_lifecycle(request: web.Request, account: Account) -> web.Response:
    holding_id = int(request.match_info["id"])
    form = await request.post()
    if not valid_csrf(request, form):
        return error_page("Проверка безопасности не пройдена.", status=403, account=account)
    db = await require_holding_action(account, holding_id, Permission.HOLDING_MANAGE)
    if db is None:
        return error_page("Недостаточно прав.", status=403, account=account)
    async with db:
        service = HoldingService(db)
        holding = await service.require_holding(holding_id)
        await service.set_holding_active(
            holding_id,
            not holding.is_active,
            actor_account_id=account.id,
        )
    raise web.HTTPFound(f"/holdings/{holding_id}")


@authenticated
async def holding_companies(request: web.Request, account: Account) -> web.Response:
    holding_id = int(request.match_info["id"])
    db = await require_holding_action(account, holding_id, Permission.HOLDING_VIEW)
    if db is None:
        return error_page("Недостаточно прав.", status=403, account=account)
    async with db:
        holding = await HoldingService(db).get_holding(holding_id)
    content = f'<div class="action-bar"><a class="button secondary-link" href="/holdings/{holding_id}">К карточке</a></div><section class="data-grid"><a class="data-card glass" href="/organizations/{holding.organization_id}"><div class="card-icon">🏢</div><div><h3>{esc(holding.organization.name)}</h3><p>Организация холдинга</p></div></a></section>'
    return page("Компании холдинга", content, account=account, active="holdings")


@authenticated
async def holding_admins(request: web.Request, account: Account) -> web.Response:
    holding_id = int(request.match_info["id"])
    db = await require_holding_action(account, holding_id, Permission.HOLDING_VIEW)
    if db is None:
        return error_page("Недостаточно прав.", status=403, account=account)
    async with db:
        assignments = list(await db.scalars(select(RoleAssignment).where(RoleAssignment.scope_type == ScopeType.HOLDING, RoleAssignment.scope_id == holding_id, RoleAssignment.is_active.is_(True)).options(selectinload(RoleAssignment.account), selectinload(RoleAssignment.role))))
    rows = [f'<div class="data-card glass"><div class="card-icon">👤</div><div><h3>{esc(item.account.full_name)}</h3><p>{esc(item.role.name)}</p></div></div>' for item in assignments]
    return page("Администраторы холдинга", f'<div class="action-bar"><a class="button secondary-link" href="/holdings/{holding_id}">К карточке</a></div>' + cards(rows, "Администраторы не назначены"), account=account, active="holdings")


@authenticated
async def holding_audit_page(request: web.Request, account: Account) -> web.Response:
    holding_id = int(request.match_info["id"])
    db = await require_holding_action(account, holding_id, Permission.HOLDING_AUDIT_VIEW)
    if db is None:
        return error_page("Недостаточно прав.", status=403, account=account)
    async with db:
        holding = await HoldingService(db).require_holding(holding_id)
        events = await HoldingAuditService(db).list_holding_events(holding_id, limit=30)
    rows = "".join(f'<article class="message glass"><b>{esc(event.title)}</b><time>{event.created_at:%d.%m.%Y %H:%M}</time><p>{esc(event.details or event.event_type)}</p></article>' for event in events)
    return page(f"История · {holding.name}", f'<div class="action-bar"><a class="button secondary-link" href="/holdings/{holding_id}">К карточке</a></div><section class="message-list">{rows or "<p>Изменений пока нет.</p>"}</section>', account=account, active="holdings")


async def visible_unit_ids(db, account: Account) -> set[int]:
    return await BusinessUnitAccessService(db).visible_unit_ids(account)


async def has_platform_access(db, account: Account) -> bool:
    assignments = list(
        await db.scalars(
            select(RoleAssignment).where(
                RoleAssignment.account_id == account.id,
                RoleAssignment.is_active.is_(True),
                RoleAssignment.revoked_at.is_(None),
            )
        )
    )
    if not assignments:
        return account.role == UserRole.ADMIN
    return any(item.scope_type == ScopeType.PLATFORM for item in assignments)


@authenticated
async def employees_page(request: web.Request, account: Account) -> web.Response:
    if not await can(account, Permission.EMPLOYEE_VIEW):
        return error_page("Недостаточно прав.", status=403, account=account)
    query = request.query.get("q", "").strip()
    role_filter = request.query.get("role", "").strip()
    async with AsyncSessionLocal() as db:
        unit_ids = await visible_unit_ids(db, account)
        statement = select(Account).where(Account.registered.is_(True))
        if not await has_platform_access(db, account):
            if not unit_ids:
                values = []
                statement = None
            else:
                statement = statement.join(
                    AccountOrganizationalUnitMembership
                ).where(
                    AccountOrganizationalUnitMembership.organizational_unit_id.in_(unit_ids),
                    AccountOrganizationalUnitMembership.is_active.is_(True),
                )
        if statement is not None and query:
            conditions = [
                Account.full_name.ilike(f"%{query}%"),
                Account.email.ilike(f"%{query}%"),
            ]
            if query.isdigit():
                conditions += [Account.id == int(query), Account.telegram_id == int(query)]
            statement = statement.where(or_(*conditions))
        if statement is not None and role_filter in {role.value for role in UserRole}:
            statement = statement.where(Account.role == UserRole(role_filter))
        if statement is not None:
            values = list(
                await db.scalars(
                    statement.distinct().order_by(Account.full_name).limit(100)
                )
            )
    items = []
    for item in values:
        presence = employee_presence(item.id, item.last_login)
        items.append(
            f'<a class="data-card glass employee-presence-card" href="/employees/{item.id}" data-presence-account="{item.id}">'
            f'<div class="card-icon">👤</div><div><h3>{esc(item.full_name)}</h3>'
            f'<p>{esc(get_role_name(item.role))} · <span class="presence-badge presence-{presence["code"]}" data-presence-label>{presence["label"]}</span></p>'
            f'<p class="presence-login">Первая авторизация: <span data-presence-workday>{presence["workday_start"]}</span> · Последний вход: <span data-presence-login>{presence["login"]}</span></p></div></a>'
        )
    invite_action = ""
    if await can(account, Permission.ROLE_ASSIGN):
        invite_action = '<a class="button" href="/admin/invitations/new">➕ Создать приглашение</a>'
    navigation = (
        '<div class="action-bar"><a class="button secondary-link" href="/employees">Все сотрудники</a>'
        '<a class="button secondary-link" href="/employees?role=coordinator">Координаторы</a>'
        '<a class="button secondary-link" href="/employees?role=operator">Операторы</a>'
        '<a class="button secondary-link" href="/employees?role=observer">Наблюдатели</a>'
        '<a class="button secondary-link" href="/employees?role=user">Пользователи</a>'
        '<a class="button secondary-link" href="/employees">🔎 Найти сотрудника</a>'
        f'{invite_action}<a class="button secondary-link" href="/">⬅️ Назад</a></div>'
    )
    return page("Сотрудники", navigation + search_form("/employees", query, "ФИО, ID, email или Telegram ID") + cards(items), account=account, active="employees")


@authenticated
async def employee_card(request: web.Request, account: Account) -> web.Response:
    if not await can(account, Permission.EMPLOYEE_VIEW):
        return error_page("Недостаточно прав.", status=403, account=account)
    async with AsyncSessionLocal() as db:
        item = await EmployeeService(db).get(int(request.match_info["id"]))
    if item is None:
        return error_page("Сотрудник не найден.", status=404, account=account)
    edit_email = (
        '<a class="button" href="/profile/email">Изменить email</a>'
        if item.id == account.id
        else ""
    )
    presence = employee_presence(item.id, item.last_login)
    tracking = tracking_account(item.id)
    tracking_form = ""
    schedule_form = ""
    schedule = schedule_for(item.id)
    snapshot = work_state_snapshot(item.id)
    if can_manage_work_tracking(account):
        session = session_for(request)
        enabled = tracking.get("enabled") is not False
        tracking_form = f'<form class="tracking-control" method="post" action="/employees/{item.id}/work-tracking"><input type="hidden" name="csrf" value="{esc(session.csrf_token)}"><input type="hidden" name="enabled" value="{0 if enabled else 1}"><button class="button secondary-link" type="submit">{"Отключить статистику" if enabled else "Включить статистику"}</button></form>'
        selected_days = set((schedule or {}).get("weekdays", [0, 1, 2, 3, 4]))
        weekday_inputs = "".join(f'<label><input type="checkbox" name="weekday" value="{index}" {"checked" if index in selected_days else ""}>{label}</label>' for index, label in enumerate(("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")))
        schedule_form = f'<form class="employee-schedule-form" method="post" action="/employees/{item.id}/schedule"><input type="hidden" name="csrf" value="{esc(session.csrf_token)}"><h3>Рабочий график</h3><div class="schedule-times"><label>Начало<input type="time" name="start" value="{esc((schedule or {}).get("start", "09:00"))}" required></label><label>Окончание<input type="time" name="end" value="{esc((schedule or {}).get("end", "18:00"))}" required></label></div><div class="schedule-weekdays">{weekday_inputs}</div><button class="button" type="submit">Сохранить график</button></form>'
    schedule_label = f'{schedule["start"]}–{schedule["end"]}' if schedule else "Не задан"
    content = f'<div class="action-bar"><a class="button secondary-link" href="/employees">⬅️ Сотрудники</a><a class="button secondary-link" href="/">⬅️ Назад</a>{edit_email}</div><section class="panel glass" data-presence-account="{item.id}"><div class="hero-icon">👤</div><h2>{esc(item.full_name)}</h2><dl><dt>ID</dt><dd>{item.id}</dd><dt>Email</dt><dd>{esc(item.email or "—")}</dd><dt>Telegram ID</dt><dd>{esc(item.telegram_id or "—")}</dd><dt>Роль</dt><dd>{esc(get_role_name(item.role))}</dd><dt>Язык</dt><dd>{esc(item.language)}</dd><dt>Доступ</dt><dd>{"Активен" if item.is_active else "Отключён"}</dd><dt>Текущий статус</dt><dd><span class="presence-badge presence-{presence["code"]}" data-presence-label>{presence["label"]}</span></dd><dt>Первая авторизация сегодня</dt><dd data-presence-workday>{presence["workday_start"]}</dd><dt>Начало работы по статусу</dt><dd>{snapshot["started_at"]}</dd><dt>Рабочий график</dt><dd>{schedule_label}</dd><dt>Переработка сегодня</dt><dd>{duration_label(snapshot["overtime_seconds"])}</dd><dt>Последний вход</dt><dd data-presence-login>{presence["login"]}</dd><dt>Источник</dt><dd data-presence-source>{"Агент рабочего ПК" if presence["source"] == "agent" else "Браузер" if presence["source"] == "browser" else "Указано сотрудником" if presence["source"] == "manual" else "Сбор отключён"}</dd></dl>{tracking_form}{schedule_form}</section>'
    return page("Карточка сотрудника", content, account=account, active="employees")


@authenticated
async def tickets_page(request: web.Request, account: Account) -> web.Response:
    if not await can(account, Permission.TICKET_VIEW):
        return error_page("Недостаточно прав.", status=403, account=account)
    query = request.query.get("q", "").strip()
    async with AsyncSessionLocal() as db:
        unit_ids = await visible_unit_ids(db, account)
        statement = select(Ticket).where(Ticket.business_unit_id.in_(unit_ids)).options(selectinload(Ticket.author), selectinload(Ticket.business_unit))
        if query:
            statement = statement.where(or_(Ticket.subject.ilike(f"%{query}%"), Ticket.id == int(query) if query.isdigit() else False))
        values = list(await db.scalars(statement.order_by(Ticket.created_at.desc()).limit(100)))
    items = [f'<a class="data-card glass" href="/tickets/{item.id}"><div class="card-icon">🎫</div><div><h3>#{item.id} · {esc(item.subject)}</h3><p>{esc(item.status.value)} · {esc(item.business_unit.name)} · {esc(item.author.full_name)}</p></div></a>' for item in values]
    return page("Тикеты", search_form("/tickets", query, "Номер или тема тикета") + cards(items), account=account, active="tickets")


@authenticated
async def ticket_card(request: web.Request, account: Account) -> web.Response:
    ticket_id = int(request.match_info["id"])
    async with AsyncSessionLocal() as db:
        unit_ids = await visible_unit_ids(db, account)
        item = await db.scalar(select(Ticket).where(Ticket.id == ticket_id, Ticket.business_unit_id.in_(unit_ids)).options(selectinload(Ticket.author), selectinload(Ticket.operator), selectinload(Ticket.business_unit)))
        if item is None:
            return error_page("Тикет недоступен.", status=403, account=account)
        messages = list(await db.execute(select(Message, Account).join(Account, Account.id == Message.account_id).where(Message.ticket_id == ticket_id).order_by(Message.created_at)))
    thread = "".join(f'<article class="message glass"><b>{esc(author.full_name)}</b><time>{esc(message.created_at.strftime("%d.%m.%Y %H:%M"))}</time><p>{esc(message.body)}</p></article>' for message, author in messages)
    content = f'<section class="panel glass"><h2>#{item.id} · {esc(item.subject)}</h2><p>{esc(item.status.value)} · {esc(item.business_unit.name)}</p></section><section class="message-list">{thread or "<p>Сообщений нет</p>"}</section>'
    return page("Карточка тикета", content, account=account, active="tickets")


@authenticated
async def reports_page(request: web.Request, account: Account) -> web.Response:
    if not await can(account, Permission.REPORT_VIEW):
        return error_page("Недостаточно прав.", status=403, account=account)
    async with AsyncSessionLocal() as db:
        units = await visible_unit_ids(db, account)
        organizations_count = len(await OrganizationAccessService(db).list_visible_organizations(account))
        holdings_count = len(await HoldingAccessService(db).list_visible_holdings(account))
        tickets_count = await db.scalar(select(func.count(Ticket.id)).where(Ticket.business_unit_id.in_(units))) or 0
        open_count = await db.scalar(
            select(func.count(Ticket.id)).where(
                Ticket.business_unit_id.in_(units),
                Ticket.status.notin_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
            )
        ) or 0
    metrics = [("Организации", organizations_count), ("Холдинги", holdings_count), ("Подразделения", len(units)), ("Всего тикетов", tickets_count), ("Открытые тикеты", open_count)]
    content = '<section class="metric-grid">' + ''.join(f'<article class="metric glass"><strong>{value}</strong><span>{label}</span></article>' for label, value in metrics) + '</section>'
    return page("Отчёты", content, account=account, active="reports")


@authenticated
async def two_factor_reset_page(request: web.Request, account: Account) -> web.Response:
    query = request.query.get("q", "").strip()
    target_text = request.query.get("account_id", "")
    async with AsyncSessionLocal() as db:
        if not await can_reset_two_factor(db, account):
            return error_page("Недостаточно прав.", status=403, account=account)
        if target_text.isdigit():
            target = await db.get(Account, int(target_text))
            if target is None or not await can_reset_two_factor_for(db, account, target):
                return error_page("Сотрудник недоступен для сброса 2FA.", status=403, account=account)
            setting = await db.get(TwoFactorSetting, target.id)
            if setting is None or not setting.is_enabled:
                return error_page("У сотрудника нет активной настройки 2FA.", status=404, account=account)
            session = session_for(request)
            content = f"""<div class="action-bar"><a class="button secondary-link" href="/access/2fa-reset">Выбрать другого сотрудника</a></div>
<section class="panel glass form-panel"><h2>Сбросить 2FA</h2><p><b>{esc(target.full_name)}</b><br>{esc(target.email or 'Email не указан')}<br>Приложение: {esc(TwoFactorService.PROVIDERS.get(setting.provider, setting.provider))}</p>
<form method="post" action="/access/2fa-reset"><input type="hidden" name="csrf" value="{esc(session.csrf_token)}"><input type="hidden" name="account_id" value="{target.id}">
<label>Причина сброса<input name="reason" maxlength="500" minlength="5" required placeholder="Например: сотрудник потерял телефон"></label>
<button class="button danger" type="submit">Подтвердить сброс и отозвать сессии</button></form>
<p class="recovery-hint">После сброса сотрудник не получит доступ к системе, пока заново не настроит 2FA.</p></section>"""
            return page("Сброс 2FA", content, account=account, active="access")

        statement = (
            select(Account)
            .join(TwoFactorSetting, TwoFactorSetting.account_id == Account.id)
            .where(Account.registered.is_(True), TwoFactorSetting.is_enabled.is_(True))
        )
        if query:
            conditions = [Account.full_name.ilike(f"%{query}%"), Account.email.ilike(f"%{query}%")]
            if query.isdigit():
                conditions.extend([Account.id == int(query), Account.telegram_id == int(query)])
            statement = statement.where(or_(*conditions))
        candidates = list(await db.scalars(statement.order_by(Account.full_name).limit(40)))
        values = []
        for target in candidates:
            if await can_reset_two_factor_for(db, account, target):
                values.append(target)
    items = [
        f'<a class="data-card glass" href="/access/2fa-reset?account_id={item.id}"><div class="card-icon">2F</div><div><h3>{esc(item.full_name)}</h3><p>#{item.id} · {esc(item.email or "без email")}</p></div></a>'
        for item in values
    ]
    return page(
        "Сброс 2FA",
        '<div class="action-bar"><a class="button secondary-link" href="/access">К доступам</a></div>'
        + search_form("/access/2fa-reset", query, "ФИО, ID, email или Telegram ID")
        + cards(items, "Сотрудники с активной 2FA не найдены"),
        account=account,
        active="access",
    )


@authenticated
async def two_factor_reset_submit(request: web.Request, account: Account) -> web.Response:
    form = await request.post()
    if not valid_csrf(request, form):
        return error_page("Проверка безопасности не пройдена.", status=403, account=account)
    target_text = str(form.get("account_id", ""))
    reason = str(form.get("reason", "")).strip()
    if not target_text.isdigit() or len(reason) < 5:
        return error_page("Укажите сотрудника и причину сброса.", status=400, account=account)
    target_id = int(target_text)
    async with AsyncSessionLocal() as db:
        target = await db.get(Account, target_id)
        if target is None or not await can_reset_two_factor_for(db, account, target):
            return error_page("Недостаточно прав для сброса.", status=403, account=account)
        setting = await db.get(TwoFactorSetting, target_id)
        if setting is None or not setting.is_enabled:
            return error_page("Активная настройка 2FA не найдена.", status=404, account=account)
        previous_provider = setting.provider
        await db.delete(setting)
        db.add(
            AccessAuditEvent(
                event_type="two_factor_reset",
                actor_account_id=account.id,
                target_account_id=target_id,
                details={"reason": reason, "previous_provider": previous_provider},
            )
        )
        await db.commit()
    revoke_account_authentication(target_id)
    return page(
        "2FA сброшена",
        f'<section class="panel glass"><h2>Готово</h2><p>Настройка 2FA для {esc(target.full_name)} удалена. Все активные сессии отозваны. При следующем входе сотрудник обязан настроить 2FA заново.</p><a class="button" href="/access/2fa-reset">К списку</a></section>',
        account=account,
        active="access",
    )


@authenticated
async def access_page(request: web.Request, account: Account) -> web.Response:
    role_access = await can(account, Permission.ROLE_ASSIGN)
    async with AsyncSessionLocal() as permission_db:
        reset_access = await can_reset_two_factor(permission_db, account)
    if not role_access and not reset_access:
        return error_page("Недостаточно прав.", status=403, account=account)
    if not role_access:
        actions = '<div class="action-bar"><a class="button" href="/access/2fa-reset">Сбросить 2FA сотрудника</a></div>'
        return page("Доступы", actions, account=account, active="access")
    show_history = request.query.get("history") == "1"
    async with AsyncSessionLocal() as db:
        platform = await AuthorizationService.can_async(account, Permission.ROLE_ASSIGN, scope=AccessScope.platform(), session=db)
        statement = select(RoleAssignment).options(selectinload(RoleAssignment.account), selectinload(RoleAssignment.role))
        if show_history:
            statement = statement.where(RoleAssignment.is_active.is_(False))
        else:
            statement = statement.where(RoleAssignment.is_active.is_(True), RoleAssignment.revoked_at.is_(None))
        if not platform:
            unit_ids = await visible_unit_ids(db, account)
            statement = statement.where(RoleAssignment.scope_type == ScopeType.BUSINESS_UNIT, RoleAssignment.scope_id.in_(unit_ids))
        values = list(await db.scalars(statement.order_by(RoleAssignment.created_at.desc()).limit(100)))
    session = session_for(request)
    rows = ''.join(
        f'<tr><td>{item.id}</td><td>{esc(item.account.full_name)}</td><td>{esc(item.role.name)}</td><td>{esc(item.scope_type.value)}</td><td>{esc(item.scope_id or "Вся платформа")}</td><td>'
        + (f'<form method="post" action="/access/assignments/{item.id}/revoke"><input type="hidden" name="csrf" value="{esc(session.csrf_token)}"><button class="button danger" type="submit">Отозвать</button></form>' if item.is_active else esc(item.revoked_at or "Отозвано"))
        + '</td></tr>' for item in values
    )
    actions = (
        '<div class="action-bar"><a class="button" href="/access/assign">➕ Назначить роль</a>'
        '<a class="button secondary-link" href="/access">📋 Активные назначения</a>'
        '<a class="button secondary-link" href="/access?history=1">🕘 История назначений</a>'
        '<a class="button secondary-link" href="/access/roles">🛡 Роли</a>'
        '<a class="button secondary-link" href="/access/permissions">🔑 Разрешения</a>'
        '<a class="button secondary-link" href="/access/audit">📜 Журнал доступа</a>'
        '<a class="button secondary-link" href="/admin/invitations/new">Пригласить по email</a>'
        '<a class="button secondary-link" href="/admin/mail">Настройки почты</a>'
        '<a class="button secondary-link" href="/access/2fa-reset">Сброс 2FA</a></div>'
    )
    return page("Доступы", actions + f'<section class="table-wrap glass"><table><thead><tr><th>ID</th><th>Сотрудник</th><th>Роль</th><th>Область</th><th>Объект</th><th>Действие</th></tr></thead><tbody>{rows}</tbody></table></section>', account=account, active="access")


async def access_target_allowed(db, actor: Account, target_id: int) -> bool:
    target = await db.get(Account, target_id)
    if target is None or not target.registered:
        return False
    if await has_platform_access(db, actor):
        return True
    unit_ids = await visible_unit_ids(db, actor)
    membership = await db.scalar(select(AccountOrganizationalUnitMembership.id).where(AccountOrganizationalUnitMembership.account_id == target_id, AccountOrganizationalUnitMembership.organizational_unit_id.in_(unit_ids), AccountOrganizationalUnitMembership.is_active.is_(True)))
    return membership is not None


@authenticated
async def access_assign_page(request: web.Request, account: Account) -> web.Response:
    if not await can(account, Permission.ROLE_ASSIGN):
        return error_page("Недостаточно прав.", status=403, account=account)
    query = request.query.get("q", "").strip()
    target_text = request.query.get("account_id", "")
    if not target_text.isdigit():
        results = []
        if len(query) >= 2:
            async with AsyncSessionLocal() as db:
                unit_ids = await visible_unit_ids(db, account)
                statement = select(Account).where(Account.registered.is_(True), or_(Account.full_name.ilike(f"%{query}%"), Account.email.ilike(f"%{query}%")))
                if query.isdigit():
                    statement = statement.where(or_(Account.id == int(query), Account.telegram_id == int(query), Account.full_name.ilike(f"%{query}%")))
                if not await has_platform_access(db, account):
                    statement = statement.join(AccountOrganizationalUnitMembership).where(AccountOrganizationalUnitMembership.organizational_unit_id.in_(unit_ids), AccountOrganizationalUnitMembership.is_active.is_(True))
                results = list(await db.scalars(statement.distinct().order_by(Account.full_name).limit(8)))
        items = [f'<a class="data-card glass" href="/access/assign?account_id={item.id}"><div class="card-icon">👤</div><div><h3>{esc(item.full_name)}</h3><p>#{item.id} · {esc(item.email or "без email")}</p></div></a>' for item in results]
        prompt = cards(items, "Введите не менее двух символов для поиска сотрудника" if len(query) < 2 else "Сотрудник не найден")
        return page("Назначить роль", '<div class="action-bar"><a class="button secondary-link" href="/access">⬅️ Доступы</a></div>' + search_form("/access/assign", query, "ФИО, ID, email или Telegram ID") + prompt, account=account, active="access")
    target_id = int(target_text)
    async with AsyncSessionLocal() as db:
        if not await access_target_allowed(db, account, target_id):
            return error_page("Сотрудник недоступен.", status=403, account=account)
        target = await db.get(Account, target_id)
        units = await BusinessUnitAccessService(db).list_visible_units(account, active=True)
        roles = await RoleGrantPolicy(db).list_grantable_business_unit_roles(account)
    role_options = ''.join(f'<option value="{esc(role.code)}">{esc(ROLE_LABELS.get(role.code, role.name))}</option>' for role in roles)
    unit_options = ''.join(f'<option value="{unit.id}">{esc(unit.name)} #{unit.id}</option>' for unit in units)
    session = session_for(request)
    content = f'''<div class="action-bar"><a class="button secondary-link" href="/access/assign">Выбрать другого сотрудника</a><a class="button secondary-link" href="/access">⬅️ Доступы</a></div><section class="panel glass form-panel"><h2>{esc(target.full_name)}</h2><form method="post" action="/access/assign"><input type="hidden" name="csrf" value="{esc(session.csrf_token)}"><input type="hidden" name="account_id" value="{target.id}"><div class="form-grid"><label>Роль<select name="role_code" required>{role_options}</select></label><label>Подразделение<select name="unit_id" required>{unit_options}</select></label><label>Основание<input name="reason" maxlength="1024" value="Назначено через веб-интерфейс"></label></div><button class="button" type="submit">Назначить роль</button></form></section>'''
    return page("Назначить роль", content, account=account, active="access")


@authenticated
async def access_assign_submit(request: web.Request, account: Account) -> web.Response:
    form = await request.post()
    if not valid_csrf(request, form):
        return error_page("Проверка безопасности не пройдена.", status=403, account=account)
    try:
        target_id = int(str(form.get("account_id", "")))
        unit_id = int(str(form.get("unit_id", "")))
    except ValueError:
        return error_page("Сотрудник или подразделение не выбраны.", account=account)
    role_code = str(form.get("role_code", ""))
    scope = AccessScope.business_unit(unit_id)
    async with AsyncSessionLocal() as db:
        if not await access_target_allowed(db, account, target_id) or not await RoleGrantPolicy(db).can_grant(account, role_code=role_code, scope=scope):
            return error_page("Недостаточно прав для назначения.", status=403, account=account)
        try:
            assignment = await RoleAssignmentService(db).assign_role(account_id=target_id, role_code=role_code, scope=scope, granted_by_account_id=account.id, grant_reason=str(form.get("reason", "")))
        except ValueError as error:
            return error_page(str(error), account=account)
    raise web.HTTPFound(f"/access#assignment-{assignment.id}")


@authenticated
async def access_assignment_revoke(request: web.Request, account: Account) -> web.Response:
    form = await request.post()
    if not valid_csrf(request, form):
        return error_page("Проверка безопасности не пройдена.", status=403, account=account)
    assignment_id = int(request.match_info["id"])
    async with AsyncSessionLocal() as db:
        assignment = await db.scalar(select(RoleAssignment).where(RoleAssignment.id == assignment_id).options(selectinload(RoleAssignment.role)))
        if assignment is None or not assignment.is_active:
            return error_page("Назначение не найдено.", status=404, account=account)
        scope = AccessScope(assignment.scope_type, assignment.scope_id)
        if not await RoleGrantPolicy(db).can_grant(account, role_code=assignment.role.code, scope=scope):
            return error_page("Недостаточно прав для отзыва.", status=403, account=account)
        try:
            await RoleAssignmentService(db).revoke_assignment(assignment_id, revoked_by_account_id=account.id, revoke_reason="Отозвано через веб-интерфейс")
        except ValueError as error:
            return error_page(str(error), account=account)
    raise web.HTTPFound("/access")


@authenticated
async def access_audit_page(request: web.Request, account: Account) -> web.Response:
    if not await can(account, Permission.ROLE_ASSIGN):
        return error_page("Недостаточно прав.", status=403, account=account)
    async with AsyncSessionLocal() as db:
        statement = select(AccessAuditEvent).options(selectinload(AccessAuditEvent.actor), selectinload(AccessAuditEvent.target_account)).order_by(AccessAuditEvent.created_at.desc(), AccessAuditEvent.id.desc()).limit(100)
        statement = await AccessAuditAccessService(db).apply_filter(statement, account)
        events = list(await db.scalars(statement))
    labels = {"role_assignment_created": "Роль назначена", "role_assignment_revoked": "Роль отозвана"}
    rows = ''.join(f'<article class="message glass"><b>{esc(labels.get(event.event_type, event.event_type))}</b><time>{event.created_at:%d.%m.%Y %H:%M}</time><p>Исполнитель: {esc(event.actor.full_name if event.actor else "система")} · Сотрудник: {esc(event.target_account.full_name if event.target_account else "—")} · Роль: {esc(event.role_code or "—")} · Область: {esc(event.scope_type.value if event.scope_type else "—")} #{esc(event.scope_id or "—")}</p></article>' for event in events)
    return page("Журнал доступа", '<div class="action-bar"><a class="button secondary-link" href="/access">⬅️ Доступы</a></div><section class="message-list">' + (rows or '<p>Событий пока нет.</p>') + '</section>', account=account, active="access")


@authenticated
async def access_roles_page(request: web.Request, account: Account) -> web.Response:
    if not await can(account, Permission.ROLE_ASSIGN):
        return error_page("Недостаточно прав.", status=403, account=account)
    async with AsyncSessionLocal() as db:
        roles = list(await db.scalars(select(Role).where(Role.is_active.is_(True)).order_by(Role.name)))
    items = [f'<article class="data-card glass"><div class="card-icon">🛡</div><div><h3>{esc(role.name)}</h3><p>{esc(role.code)} · {esc(role.description or "Без описания")}</p></div></article>' for role in roles]
    return page("Роли", '<div class="action-bar"><a class="button secondary-link" href="/access">⬅️ Доступы</a></div>' + cards(items), account=account, active="access")


@authenticated
async def access_permissions_page(request: web.Request, account: Account) -> web.Response:
    if not await can(account, Permission.ROLE_ASSIGN):
        return error_page("Недостаточно прав.", status=403, account=account)
    items = [f'<article class="data-card glass"><div class="card-icon">🔑</div><div><h3>{esc(permission.value)}</h3><p>{esc(get_permission_name(permission))}</p></div></article>' for permission in Permission]
    return page("Разрешения", '<div class="action-bar"><a class="button secondary-link" href="/access">⬅️ Доступы</a></div>' + cards(items), account=account, active="access")


@authenticated
async def mail_settings_page(request: web.Request, account: Account) -> web.Response:
    if not await can(account, Permission.ROLE_ASSIGN):
        return error_page("Недостаточно прав.", status=403, account=account)
    async with AsyncSessionLocal() as db:
        mail = await db.get(MailSettings, 1)
    session = session_for(request)
    values = {
        "host": mail.smtp_host if mail else "",
        "port": mail.smtp_port if mail else 587,
        "username": mail.smtp_username if mail else "",
        "from_email": mail.from_email if mail else "",
        "from_name": mail.from_name if mail else "SupportBot Enterprise",
        "starttls": bool(mail.use_starttls) if mail else True,
        "active": bool(mail.is_active) if mail else True,
    }
    content = f'''<section class="panel glass form-panel"><h2>SMTP-сервер</h2>
<p>Пароль сохраняется на сервере в зашифрованном виде.</p>
<form method="post" action="/admin/mail"><input type="hidden" name="csrf" value="{esc(session.csrf_token)}">
<div class="form-grid"><label>SMTP host<input name="host" value="{esc(values['host'])}" required></label>
<label>Порт<input type="number" name="port" value="{values['port']}" min="1" max="65535" required></label>
<label>Пользователь<input name="username" value="{esc(values['username'])}"></label>
<label>Пароль<input type="password" name="password" placeholder="Оставьте пустым, чтобы не менять"></label>
<label>Email отправителя<input type="email" name="from_email" value="{esc(values['from_email'])}" required></label>
<label>Имя отправителя<input name="from_name" value="{esc(values['from_name'])}" required></label></div>
<label class="radio"><input type="checkbox" name="starttls" {'checked' if values['starttls'] else ''}><span>Использовать STARTTLS</span></label>
<label class="radio"><input type="checkbox" name="active" {'checked' if values['active'] else ''}><span>Отправка включена</span></label>
<button class="button" type="submit">Сохранить</button></form></section>'''
    return page("Настройки почты", content, account=account, active="access")


@authenticated
async def mail_settings_update(request: web.Request, account: Account) -> web.Response:
    if not await can(account, Permission.ROLE_ASSIGN):
        return error_page("Недостаточно прав.", status=403, account=account)
    form = await request.post()
    if not valid_csrf(request, form):
        return error_page("Проверка безопасности не пройдена.", status=403, account=account)
    try:
        port = int(str(form.get("port", "")))
        if not 1 <= port <= 65535:
            raise ValueError
        from_email = WebIdentityService.normalize_email(str(form.get("from_email", "")))
    except ValueError:
        return error_page("Проверьте порт и email отправителя.", account=account)
    host = str(form.get("host", "")).strip()
    from_name = " ".join(str(form.get("from_name", "")).split())
    if not host or not from_name:
        return error_page("Заполните обязательные поля.", account=account)
    async with AsyncSessionLocal() as db:
        mail = await db.get(MailSettings, 1)
        if mail is None:
            mail = MailSettings(
                id=1,
                smtp_host=host,
                smtp_port=port,
                from_email=from_email,
                from_name=from_name,
            )
            db.add(mail)
        mail.smtp_host = host
        mail.smtp_port = port
        mail.smtp_username = str(form.get("username", "")).strip() or None
        mail.from_email = from_email
        mail.from_name = from_name
        mail.use_starttls = form.get("starttls") == "on"
        mail.is_active = form.get("active") == "on"
        password = str(form.get("password", ""))
        if password:
            mail.smtp_password_encrypted = WebIdentityService.encrypt_secret(password)
        await db.commit()
    raise web.HTTPFound("/admin/mail")


@authenticated
async def invitation_page(request: web.Request, account: Account) -> web.Response:
    if not await can(account, Permission.ROLE_ASSIGN):
        return error_page("Недостаточно прав.", status=403, account=account)
    async with AsyncSessionLocal() as db:
        units = await BusinessUnitAccessService(db).list_visible_units(
            account,
            active=True,
        )
    session = session_for(request)
    unit_options = "".join(
        f'<option value="{unit.id}">{esc(unit.name)}</option>' for unit in units
    )
    role_options = "".join(
        f'<option value="{role.value}">{esc(role.value)}</option>'
        for role in InviteRole
    )
    content = f'''<section class="panel glass form-panel"><h2>Email-приглашение</h2>
<form method="post" action="/admin/invitations"><input type="hidden" name="csrf" value="{esc(session.csrf_token)}">
<div class="form-grid"><label>ФИО<input name="full_name" required minlength="2" maxlength="255"></label>
<label>Email<input type="email" name="email" required></label>
<label>Роль<select name="role" required>{role_options}</select></label>
<label>Подразделение<select name="unit_id" required>{unit_options}</select></label></div>
<button class="button" type="submit">Создать и отправить</button></form></section>'''
    return page("Приглашение сотрудника", content, account=account, active="access")


@authenticated
async def invitation_create(request: web.Request, account: Account) -> web.Response:
    if not await can(account, Permission.ROLE_ASSIGN):
        return error_page("Недостаточно прав.", status=403, account=account)
    form = await request.post()
    if not valid_csrf(request, form):
        return error_page("Проверка безопасности не пройдена.", status=403, account=account)
    try:
        email = WebIdentityService.normalize_email(str(form.get("email", "")))
        role = InviteRole(str(form.get("role", "")))
        unit_id = int(str(form.get("unit_id", "")))
    except (ValueError, TypeError):
        return error_page("Проверьте email, роль и подразделение.", account=account)
    full_name = " ".join(str(form.get("full_name", "")).split())
    if len(full_name) < 2 or len(full_name) > 255:
        return error_page("Проверьте ФИО.", account=account)
    async with AsyncSessionLocal() as db:
        if role == InviteRole.ADMIN and not await has_platform_access(db, account):
            return error_page(
                "Назначать администратора может только администратор платформы.",
                status=403,
                account=account,
            )
        unit_access = BusinessUnitAccessService(db)
        if not await unit_access.can_access_unit(account, unit_id):
            return error_page("Подразделение недоступно.", status=403, account=account)
        duplicate = await db.scalar(
            select(Account.id).where(func.lower(Account.email) == email)
        )
        if duplicate is not None:
            return error_page("Аккаунт с таким email уже существует.", status=409, account=account)
        token = InviteService.generate_token()
        invite = Invite(
            token_hash=InviteService.make_token_hash(token),
            full_name=full_name,
            email=email,
            delivery_channel="email",
            role=role,
            organizational_unit_id=unit_id,
            created_by_id=account.id,
            expires_at=now() + timedelta(days=7),
            is_active=True,
        )
        db.add(invite)
        await db.flush()
        link = f"{WEB_PUBLIC_URL}/register?token={token}"
        try:
            await WebIdentityService(db).send_email(
                recipient=email,
                subject="Приглашение в SupportBot Enterprise",
                text=(
                    f"Здравствуйте, {full_name}!\n\n"
                    "Вас пригласили в SupportBot Enterprise. "
                    "Для регистрации перейдите по ссылке:\n"
                    f"{link}\n\nСсылка действует 7 дней."
                ),
            )
        except (OSError, ValueError) as error:
            await db.rollback()
            return error_page(f"Не удалось отправить письмо: {error}", status=502, account=account)
        await db.commit()
    return page("Приглашение отправлено", f'<section class="panel glass"><h2>Готово</h2><p>Приглашение отправлено на {esc(email)}.</p><a class="button" href="/employees">К сотрудникам</a></section>', account=account, active="access")


@authenticated
async def profile_page(request: web.Request, account: Account) -> web.Response:
    permissions = sorted(get_permission_name(permission) for permission in role_permissions(account.role))
    permissions_html = ''.join(f'<li>✅ {esc(permission)}</li>' for permission in permissions) or '<li>Нет разрешений</li>'
    content = f'<div class="action-bar"><a class="button" href="/profile/email">Изменить email</a></div><section class="panel glass"><div class="hero-icon">👤</div><h2>{esc(account.full_name)}</h2><dl><dt>ID</dt><dd>{account.id}</dd><dt>Email</dt><dd>{esc(account.email or "—")}</dd><dt>Telegram ID</dt><dd>{esc(account.telegram_id or "—")}</dd><dt>Роль</dt><dd>{esc(get_role_name(account.role))}</dd><dt>Язык</dt><dd>{esc(account.language)}</dd><dt>Активен</dt><dd>{"да" if account.is_active else "нет"}</dd><dt>Зарегистрирован</dt><dd>{"да" if account.registered else "нет"}</dd></dl><div class="card-section"><h3>Разрешения</h3><ul>{permissions_html}</ul></div></section>'
    return page("Профиль", content, account=account, active="profile")


@authenticated
async def profile_email_page(request: web.Request, account: Account) -> web.Response:
    async with AsyncSessionLocal() as db:
        organization = await account_primary_organization(db, account.id)
        pending = await db.scalar(
            select(EmailChangeRequest).where(EmailChangeRequest.account_id == account.id)
        )
        setting = await db.get(TwoFactorSetting, account.id)
    domains = organization_email_domains(organization) if organization else []
    session = session_for(request)
    if organization is None:
        return error_page(
            "Основная организация сотрудника не определена. Обратитесь к администратору.",
            status=409,
            account=account,
        )
    if not domains:
        return error_page(
            "Смена email недоступна: в карточке Вашей организации не настроены разрешённые почтовые домены.",
            status=409,
            account=account,
        )
    if setting is None or not setting.is_enabled:
        return error_page("Для изменения email необходимо настроить 2FA.", status=403, account=account)
    pending_active = pending is not None and pending.expires_at > now() and pending.attempts < EMAIL_CHANGE_MAX_ATTEMPTS
    confirmation = ""
    if pending_active:
        confirmation = f'''<section class="panel glass form-panel"><h2>Подтвердите новый адрес</h2>
<p>Мы отправили шестизначный код на <b>{esc(pending.new_email)}</b>. Код действует 15 минут. Введите его вместе с текущим кодом приложения 2FA.</p>
<form method="post" action="/profile/email/confirm" data-auto-code-form><input type="hidden" name="csrf" value="{esc(session.csrf_token)}">
<div class="form-grid"><label>Код из письма<input name="email_code" inputmode="numeric" pattern="[0-9]{{6}}" maxlength="6" autocomplete="one-time-code" required data-auto-code></label>
<label>Код 2FA<input name="totp_code" inputmode="numeric" pattern="[0-9]{{6}}" maxlength="6" autocomplete="one-time-code" required data-auto-code></label></div>
</form></section>'''
    content = f'''<div class="action-bar"><a class="button secondary-link" href="/profile">К профилю</a></div>
<section class="panel glass form-panel"><h2>Новый email</h2>
<p>Текущий адрес: <b>{esc(account.email or "не указан")}</b><br>Организация: <b>{esc(organization.name)}</b><br>Разрешены: <b>{esc(", ".join("@" + item for item in domains))}</b></p>
<form method="post" action="/profile/email/request"><input type="hidden" name="csrf" value="{esc(session.csrf_token)}">
<label>Новый email<input type="email" name="email" maxlength="320" required autocomplete="email"></label>
<button class="button" type="submit">Отправить код подтверждения</button></form></section>{confirmation}'''
    return page("Изменение email", content, account=account, active="profile")


@authenticated
async def profile_email_request(request: web.Request, account: Account) -> web.Response:
    form = await request.post()
    if not valid_csrf(request, form):
        return error_page("Проверка безопасности не пройдена.", status=403, account=account)
    try:
        new_email = WebIdentityService.normalize_email(str(form.get("email", "")))
        new_domain = email_domain(new_email)
    except (ValueError, UnicodeError):
        return error_page("Укажите корректный email.", account=account)
    async with AsyncSessionLocal() as db:
        organization = await account_primary_organization(db, account.id)
        domains = organization_email_domains(organization) if organization else []
        if not domains or new_domain not in domains:
            return error_page(
                "Добавление такого почтового адреса запрещено правилами Вашей организации.",
                status=403,
                account=account,
            )
        if account.email and new_email == account.email.casefold():
            return error_page("Этот email уже указан в Вашем профиле.", status=409, account=account)
        duplicate = await db.scalar(
            select(Account.id).where(func.lower(Account.email) == new_email, Account.id != account.id)
        )
        if duplicate is not None:
            return error_page("Этот email уже используется другим сотрудником.", status=409, account=account)
        setting = await db.get(TwoFactorSetting, account.id)
        if setting is None or not setting.is_enabled:
            return error_page("Для изменения email необходимо настроить 2FA.", status=403, account=account)
        pending = await db.scalar(
            select(EmailChangeRequest).where(EmailChangeRequest.account_id == account.id)
        )
        current_time = now()
        if pending is not None and pending.last_sent_at + EMAIL_CHANGE_RESEND > current_time:
            return error_page("Повторный код можно запросить через минуту.", status=429, account=account)
        code = str(secrets.randbelow(1_000_000)).zfill(6)
        if pending is None:
            pending = EmailChangeRequest(
                account_id=account.id,
                new_email=new_email,
                code_hash=email_change_code_hash(account.id, new_email, code),
                expires_at=current_time + EMAIL_CHANGE_TTL,
                attempts=0,
                last_sent_at=current_time,
            )
            db.add(pending)
        else:
            pending.new_email = new_email
            pending.code_hash = email_change_code_hash(account.id, new_email, code)
            pending.expires_at = current_time + EMAIL_CHANGE_TTL
            pending.attempts = 0
            pending.last_sent_at = current_time
        try:
            await WebIdentityService(db).send_email(
                recipient=new_email,
                subject="Подтверждение нового email — SupportBot Enterprise",
                text=(
                    f"Здравствуйте, {account.full_name}!\n\nКод подтверждения нового email: {code}\n"
                    "Код действует 15 минут. Для завершения также потребуется код приложения 2FA.\n\n"
                    "Если Вы не запрашивали изменение, ничего не вводите и сообщите администратору."
                ),
                html=f'''<!doctype html><html><body style="margin:0;background:#090b0e;color:#f7f2e8;font-family:Arial,sans-serif"><table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td align="center" style="padding:36px 16px"><table role="presentation" width="560" style="max-width:100%;background:#171b21;border:1px solid #65583f;border-radius:18px"><tr><td style="padding:34px"><div style="color:#e4c78f;font-size:14px;letter-spacing:2px">SUPPORTBOT ENTERPRISE</div><h1 style="font-size:25px;margin:18px 0 10px;color:#f7f2e8">Подтвердите новый email</h1><p style="color:#c8c1b5;line-height:1.6">Здравствуйте, {esc(account.full_name)}! Введите этот код в профиле и подтвердите действие кодом приложения 2FA.</p><div style="margin:28px 0;padding:18px;text-align:center;background:#0d1116;border:1px solid #373d46;border-radius:12px;color:#e4c78f;font-size:34px;font-weight:bold;letter-spacing:9px">{code}</div><p style="color:#c8c1b5;line-height:1.6">Код действует 15 минут. Если Вы не запрашивали изменение адреса, ничего не вводите и сообщите администратору.</p></td></tr></table></td></tr></table></body></html>''',
            )
        except (OSError, ValueError) as error:
            await db.rollback()
            return error_page(f"Не удалось отправить письмо: {error}", status=502, account=account)
        await db.commit()
    raise web.HTTPFound("/profile/email")


@authenticated
async def profile_email_confirm(request: web.Request, account: Account) -> web.Response:
    form = await request.post()
    if not valid_csrf(request, form):
        return error_page("Проверка безопасности не пройдена.", status=403, account=account)
    email_code = str(form.get("email_code", "")).strip()
    totp_code = str(form.get("totp_code", "")).strip()
    async with AsyncSessionLocal() as db:
        pending = await db.scalar(
            select(EmailChangeRequest).where(EmailChangeRequest.account_id == account.id).with_for_update()
        )
        if pending is None or pending.expires_at <= now() or pending.attempts >= EMAIL_CHANGE_MAX_ATTEMPTS:
            if pending is not None:
                await db.delete(pending)
                await db.commit()
            return error_page("Код истёк. Запросите новый код.", status=410, account=account)
        expected = email_change_code_hash(account.id, pending.new_email, email_code)
        if len(email_code) != 6 or not email_code.isdigit() or not hmac.compare_digest(expected, pending.code_hash):
            pending.attempts += 1
            await db.commit()
            return error_page("Неверный код из письма.", status=403, account=account)
        organization = await account_primary_organization(db, account.id)
        domains = organization_email_domains(organization) if organization else []
        if not domains or email_domain(pending.new_email) not in domains:
            await db.delete(pending)
            await db.commit()
            return error_page(
                "Добавление такого почтового адреса запрещено правилами Вашей организации.",
                status=403,
                account=account,
            )
        duplicate = await db.scalar(
            select(Account.id).where(func.lower(Account.email) == pending.new_email, Account.id != account.id)
        )
        if duplicate is not None:
            return error_page("Этот email уже используется другим сотрудником.", status=409, account=account)
        setting = await db.get(TwoFactorSetting, account.id, with_for_update=True)
        if setting is None or not setting.is_enabled:
            return error_page("Активная настройка 2FA не найдена.", status=403, account=account)
        if not await TwoFactorService(db).verify_totp_only(setting, totp_code):
            return error_page("Неверный или уже использованный код 2FA.", status=403, account=account)
        target = await db.get(Account, account.id, with_for_update=True)
        previous_email = target.email
        target.email = pending.new_email
        target.email_verified_at = now()
        db.add(
            AccessAuditEvent(
                event_type="account_email_changed",
                actor_account_id=account.id,
                target_account_id=account.id,
                details={"previous_email": previous_email, "new_email": pending.new_email},
            )
        )
        await db.delete(pending)
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            return error_page("Не удалось сохранить email. Возможно, адрес уже занят.", status=409, account=account)
    revoke_account_authentication(account.id)
    response = page(
        "Email изменён",
        f'<section class="panel glass"><h2>Адрес подтверждён</h2><p>Новый email <b>{esc(target.email)}</b> сохранён. В целях безопасности выполните вход заново.</p><a class="button" href="/login">Войти</a></section>',
    )
    response.del_cookie(SESSION_COOKIE, path="/")
    return response


async def guest_language_page(request: web.Request) -> web.Response:
    guest = request["guest_language_session"]
    query = request.query.get("q", "").strip()
    popular = ["Русский", "English", "Deutsch", "Español", "Français", "中文"]
    popular_forms = []
    for name in popular:
        try:
            meta = LanguagePackService.resolve_language(name)
            flag = GuestLanguageService.flag(meta["code"])
            popular_forms.append(
                f'<form method="post" action="/auth/language/install" class="language-choice-card glass">'
                f'<input type="hidden" name="csrf" value="{esc(guest.csrf_token)}">'
                f'<input type="hidden" name="query" value="{esc(name)}">'
                f'<button type="submit"><span class="language-choice-flag">{esc(flag)}</span>'
                f'<span><b>{esc(meta["native"])}</b><small>{esc(meta["english"])}</small></span></button></form>'
            )
        except Exception:
            continue
    result = ""
    if query:
        try:
            meta = LanguagePackService.resolve_language(query)
            result = (
                f'<form method="post" action="/auth/language/install" class="language-choice-card language-search-result glass">'
                f'<input type="hidden" name="csrf" value="{esc(guest.csrf_token)}">'
                f'<input type="hidden" name="query" value="{esc(query)}">'
                f'<button type="submit"><span class="language-choice-flag">{esc(GuestLanguageService.flag(meta["code"]))}</span>'
                f'<span><b>{esc(meta["native"])}</b><small>{esc(meta["english"])} · {esc(meta["code"])}</small></span></button></form>'
            )
        except Exception:
            result = '<p class="language-progress-error">Язык не найден.</p>'
    content = f'''<section class="login-card glass hybrid-login recovery-card guest-language-card"><div class="login-logo">S</div>
<h2>Язык интерфейса</h2><p>Выберите язык авторизации</p>
<form class="guest-language-search" method="get" action="/auth/language"><input name="q" value="{esc(query)}" placeholder="Введите название языка" required><button type="submit">Найти</button></form>
{result}<h3>Популярные языки</h3><div class="language-choice-grid">{''.join(popular_forms)}</div>
<a class="forgot-password recovery-back" href="/login">Вернуться ко входу</a></section>'''
    return page("Язык интерфейса", content, body_class="login-page")


async def run_guest_language_job(job_id: str) -> None:
    job = GUEST_LANGUAGE_JOBS[job_id]
    try:
        job.status = "running"
        job.progress = 12
        await asyncio.sleep(0.15)
        meta = await asyncio.to_thread(GuestLanguageService.install, job.query)
        job.language_code = meta["code"]
        job.flag = GuestLanguageService.flag(meta["code"])
        job.progress = 72
        if not LanguagePackService.is_installed(meta["code"]):
            await LanguagePackService.install_language_pack(job.query)
        job.progress = 92
        for _ in range(12):
            if job.heartbeat_count > 0 and job.last_seen_at + timedelta(seconds=3) > now():
                break
            await asyncio.sleep(0.5)
        guest = GUEST_LANGUAGE_SESSIONS.get(job.guest_id)
        if (
            guest is None
            or guest.expires_at <= now()
            or job.heartbeat_count == 0
            or job.last_seen_at + timedelta(seconds=3) <= now()
        ):
            job.status = "cancelled"
            job.error = "Загрузка остановлена: гостевая сессия прервана."
            job.message = job.failure_message
            await remove_interrupted_guest_language(job_id, job)
            return
        guest.language_code = meta["code"]
        marker = guest_language_marker(meta["code"])
        if marker.exists():
            marker.unlink()
        job.progress = 100
        job.message = job.complete_message
        job.status = "complete"
    except Exception as error:
        logger.exception("Guest language installation failed")
        await remove_interrupted_guest_language(job_id, job)
        job.status = "failed"
        job.error = str(error)
        job.message = job.failure_message


async def guest_language_install(request: web.Request) -> web.Response:
    guest_id = request["guest_language_id"]
    guest = request["guest_language_session"]
    form = await request.post()
    if not secrets.compare_digest(str(form.get("csrf", "")), guest.csrf_token):
        return error_page("Проверка безопасности не пройдена.", status=403)
    query = str(form.get("query", "")).strip()
    try:
        meta = LanguagePackService.resolve_language(query)
    except Exception:
        return error_page("Язык не найден.")
    install_title, initial_message, complete_message, failure_message = await asyncio.to_thread(
        LanguagePackService._translate_values,
        [
            "Установка языка",
            "Подготавливаем перевод интерфейса",
            "Язык установлен",
            "Не удалось установить язык.",
        ],
        meta["code"],
    )
    package_preexisting = LanguagePackService.is_installed(meta["code"])
    web_translation_preexisting = GuestLanguageService.installed(meta["code"])
    if not package_preexisting:
        marker = guest_language_marker(meta["code"])
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(now().isoformat(), encoding="utf-8")
    job_id = secrets.token_urlsafe(18)
    flag = GuestLanguageService.flag(meta["code"])
    GUEST_LANGUAGE_JOBS[job_id] = GuestLanguageJob(
        guest_id=guest_id,
        query=query,
        language_code=meta["code"],
        language_name=f'{meta["native"]} / {meta["english"]}',
        flag=flag,
        progress=3,
        message=initial_message,
        complete_message=complete_message,
        failure_message=failure_message,
        package_preexisting=package_preexisting,
        web_translation_preexisting=web_translation_preexisting,
        last_seen_at=now(),
        heartbeat_count=0,
        status="queued",
        created_at=now(),
    )
    task = asyncio.create_task(run_guest_language_job(job_id))
    GUEST_LANGUAGE_TASKS.add(task)
    task.add_done_callback(GUEST_LANGUAGE_TASKS.discard)
    content = f'''<section class="login-card glass hybrid-login recovery-card guest-language-progress"><div class="language-flag-hero" role="img" aria-label="Флаг выбранного языка">{esc(flag)}</div>
<h2>{esc(meta["native"])}</h2><p id="guest-language-message">{esc(initial_message)}</p>
<div class="progress-track" role="progressbar" aria-valuemin="0" aria-valuemax="100"><div class="progress-fill" id="guest-language-progress" style="width:3%"></div></div>
<strong id="guest-language-percent">3%</strong><p class="language-progress-error" id="guest-language-error"></p></section>
<script>(function(){{function poll(){{var xhr=new XMLHttpRequest();xhr.open("GET","/auth/language/jobs/{job_id}",true);xhr.setRequestHeader("Cache-Control","no-store");xhr.onreadystatechange=function(){{if(xhr.readyState!==4)return;if(xhr.status!==200){{window.setTimeout(poll,900);return;}}var job=JSON.parse(xhr.responseText);document.getElementById("guest-language-message").textContent=job.message;document.getElementById("guest-language-progress").style.width=job.progress+"%";document.getElementById("guest-language-percent").textContent=job.progress+"%";if(job.status==="complete"){{window.location.replace("/login");return;}}if(job.status==="failed"||job.status==="cancelled"){{document.getElementById("guest-language-error").textContent=job.error;return;}}window.setTimeout(poll,650);}};xhr.send();}}window.setTimeout(poll,350);}}());</script>'''
    return page(install_title, content, body_class="login-page")


async def guest_language_job_status(request: web.Request) -> web.Response:
    job = GUEST_LANGUAGE_JOBS.get(request.match_info["job_id"])
    if (
        job is None
        or job.guest_id != request["guest_language_id"]
        or now() - job.created_at > timedelta(minutes=30)
    ):
        return web.json_response({"error": "Задача не найдена."}, status=404)
    job.last_seen_at = now()
    job.heartbeat_count += 1
    return web.json_response(
        {"status": job.status, "progress": job.progress, "message": job.message, "error": job.error or ""},
        headers={"Cache-Control": "no-store"},
    )


@authenticated
async def language_page(request: web.Request, account: Account) -> web.Response:
    session = session_for(request)
    query = request.query.get("q", "").strip()
    cards_html = ""
    message = "Введите название языка и нажмите «Найти»."
    if query:
        try:
            meta = LanguagePackService.resolve_language(query)
            code = meta["code"]
            installed = LanguagePackService.is_installed(code)
            cards_html = f'''<form method="post" action="/language/install" class="language-card data-card glass"><input type="hidden" name="csrf" value="{esc(session.csrf_token)}"><input type="hidden" name="query" value="{esc(query)}"><div class="card-icon">{"✅" if account.language == code else "🌐"}</div><div><h3>{esc(meta['native'])} / {esc(meta['english'])}</h3><p>{esc(code)} · {"установлен" if installed else "будет установлен"}</p></div><button class="language-card-submit" type="submit" aria-label="Выбрать язык">›</button></form>'''
            message = "Нажмите на карточку, чтобы выбрать язык."
        except Exception:
            message = "Язык не найден. Проверьте название и попробуйте снова."
    cleanup_action = ""
    if account.role in {UserRole.ADMIN, UserRole.COORDINATOR}:
        cleanup_action = '<a class="button secondary-link" href="/language/cleanup">Очистить неиспользуемые языки</a>'
    content = f'''<div class="action-bar">{cleanup_action}</div><section class="panel glass"><h2>🌐 Language</h2><p>Введите любой язык, например: English, Русский, Deutsch или Chinese Simplified.</p><form class="search glass" method="get" action="/language"><input name="q" value="{esc(query)}" placeholder="Type your language" required><button type="submit">Найти</button></form></section><p class="language-hint">{esc(message)}</p><section class="data-grid">{cards_html}</section>'''
    return page("Language", content, account=account, active="language")


def can_cleanup_languages(account: Account) -> bool:
    return account.role in {UserRole.ADMIN, UserRole.COORDINATOR}


@authenticated
async def language_cleanup_page(request: web.Request, account: Account) -> web.Response:
    if not can_cleanup_languages(account):
        return error_page("Недостаточно прав.", status=403, account=account)
    removable = set(await LanguageCleanupService.list_removable_languages())
    removable -= active_guest_language_codes()
    session = session_for(request)
    rows = "".join(
        f'<div class="list-row"><b>{esc(code)}</b><span>Не используется активными сотрудниками</span></div>'
        for code in sorted(removable)
    ) or '<p>Неиспользуемых языковых пакетов нет.</p>'
    button = (
        '<button class="button danger" type="submit">Удалить все неиспользуемые языки</button>'
        if removable else ""
    )
    content = f'''<div class="action-bar"><a class="button secondary-link" href="/language">К языкам</a></div>
<section class="panel glass form-panel"><h2>Очистка языковых пакетов</h2>
<p>Русский и английский защищены от удаления. Язык также не будет удалён, если его использует хотя бы один активный сотрудник или сейчас выполняется его установка.</p>
<div class="language-cleanup-list">{rows}</div>
<form method="post" action="/language/cleanup"><input type="hidden" name="csrf" value="{esc(session.csrf_token)}">{button}</form></section>'''
    return page("Очистка языков", content, account=account, active="language")


@authenticated
async def language_cleanup_submit(request: web.Request, account: Account) -> web.Response:
    if not can_cleanup_languages(account):
        return error_page("Недостаточно прав.", status=403, account=account)
    form = await request.post()
    if not valid_csrf(request, form):
        return error_page("Проверка безопасности не пройдена.", status=403, account=account)
    removable = set(await LanguageCleanupService.list_removable_languages())
    removable -= active_guest_language_codes()
    removed = []
    for code in sorted(removable):
        if await LanguageCleanupService.remove_if_unused(code):
            removed.append(code)
    async with AsyncSessionLocal() as db:
        db.add(
            AccessAuditEvent(
                event_type="unused_languages_cleaned",
                actor_account_id=account.id,
                target_account_id=account.id,
                details={"removed_languages": removed},
            )
        )
        await db.commit()
    result = ", ".join(removed) if removed else "ничего не удалено"
    return page(
        "Очистка завершена",
        f'<section class="panel glass"><h2>Готово</h2><p>Результат: {esc(result)}.</p><a class="button" href="/language/cleanup">Вернуться</a></section>',
        account=account,
        active="language",
    )


async def run_language_install_job(job_id: str) -> None:
    job = LANGUAGE_INSTALL_JOBS[job_id]
    try:
        job.status = "running"
        job.progress = 5
        translated = LanguagePackService.translate_progress_message(
            job.query,
            5,
            "Язык устанавливается, ожидайте",
        )
        job.message = translated.rsplit("\n\n", 1)[-1]
        await asyncio.sleep(0)
        job.progress = 20
        if not LanguagePackService.is_installed(job.language_code):
            meta = await LanguagePackService.install_language_pack(job.query)
            job.language_code = meta["code"]
        job.progress = 90
        async with AsyncSessionLocal() as db:
            stored = await db.get(Account, job.account_id)
            if stored is None or not stored.is_active:
                raise ValueError("Аккаунт недоступен.")
            stored.language = job.language_code
            await db.commit()
        job.progress = 100
        job.status = "complete"
    except Exception as error:
        job.status = "failed"
        job.error = str(error)
        job.message = "Не удалось установить язык."


@authenticated
async def language_install_start(request: web.Request, account: Account) -> web.Response:
    form = await request.post()
    if not valid_csrf(request, form):
        return error_page("Проверка безопасности не пройдена.", status=403, account=account)
    query = str(form.get("query", "")).strip()
    if not query:
        return error_page("Введите название языка.", account=account)
    try:
        meta = LanguagePackService.resolve_language(query)
    except Exception:
        return error_page("Язык не найден.", account=account)
    job_id = secrets.token_urlsafe(18)
    LANGUAGE_INSTALL_JOBS[job_id] = LanguageInstallJob(
        account_id=account.id,
        query=query,
        language_code=meta["code"],
        language_name=f"{meta['native']} / {meta['english']}",
        progress=1,
        message="Язык устанавливается, ожидайте",
        status="queued",
        created_at=now(),
    )
    task = asyncio.create_task(run_language_install_job(job_id))
    LANGUAGE_INSTALL_TASKS.add(task)
    task.add_done_callback(LANGUAGE_INSTALL_TASKS.discard)
    content = f'''<section class="panel glass language-progress-panel"><div class="hero-icon">🌐</div><h2>{esc(meta['native'])}</h2><p id="install-message">{esc(LANGUAGE_INSTALL_JOBS[job_id].message)}</p><div class="progress-track" role="progressbar" aria-valuemin="0" aria-valuemax="100"><div class="progress-fill" id="install-progress" style="width:1%"></div></div><strong id="install-percent">1%</strong><p class="language-progress-error" id="install-error"></p></section><script>
const pollLanguage = async () => {{
  const response = await fetch('/language/jobs/{job_id}', {{cache: 'no-store'}});
  const job = await response.json();
  document.getElementById('install-message').textContent = job.message;
  document.getElementById('install-progress').style.width = job.progress + '%';
  document.getElementById('install-percent').textContent = job.progress + '%';
  if (job.status === 'complete') {{ window.location.replace('/language'); return; }}
  if (job.status === 'failed') {{ document.getElementById('install-error').textContent = job.error; return; }}
  window.setTimeout(pollLanguage, 700);
}};
window.setTimeout(pollLanguage, 350);
</script>'''
    return page("Установка языка", content, account=account, active="language")


@authenticated
async def language_install_status(request: web.Request, account: Account) -> web.Response:
    job = LANGUAGE_INSTALL_JOBS.get(request.match_info["job_id"])
    if job is None or job.account_id != account.id or now() - job.created_at > timedelta(minutes=30):
        return web.json_response({"error": "Задача не найдена."}, status=404)
    return web.json_response({"status": job.status, "progress": job.progress, "message": job.message, "error": job.error or ""})


def create_application() -> web.Application:
    application = web.Application(
        middlewares=[
            embedded_client_middleware,
            guest_language_middleware,
            response_performance_middleware,
            account_middleware,
        ],
        client_max_size=1024 * 1024,
    )
    application.on_startup.append(cleanup_abandoned_guest_language_markers)
    application.router.add_static("/static/", STATIC_ROOT)
    application.router.add_get("/styles.css", lambda _: web.FileResponse(STATIC_ROOT / "styles.css"))
    application.router.add_get("/app.js", lambda _: web.FileResponse(STATIC_ROOT / "app.js"))
    application.router.add_get("/login", login_page)
    application.router.add_get("/auth/language", guest_language_page)
    application.router.add_post("/auth/language/install", guest_language_install)
    application.router.add_get("/auth/language/jobs/{job_id}", guest_language_job_status)
    application.router.add_get("/auth/2fa/admin-recovery", admin_two_factor_recovery_page)
    application.router.add_post("/auth/2fa/admin-recovery/request", admin_two_factor_recovery_request)
    application.router.add_post("/auth/2fa/admin-recovery/verify", admin_two_factor_recovery_verify)
    application.router.add_get("/auth/2fa/{token}", two_factor_start)
    application.router.add_post("/auth/2fa/{token}/provider", two_factor_select_provider)
    application.router.add_get("/auth/2fa/{token}/setup", two_factor_setup)
    application.router.add_get("/auth/2fa/{token}/qr", two_factor_qr)
    application.router.add_post("/auth/2fa/{token}/confirm", two_factor_confirm_enrollment)
    application.router.add_post("/auth/2fa/{token}/activate", two_factor_activate)
    application.router.add_post("/auth/2fa/{token}/verify", two_factor_verify_login)
    application.router.add_post("/auth/email", email_login)
    application.router.add_get("/auth/recovery", password_recovery_page)
    application.router.add_post("/auth/recovery/request", password_recovery_request)
    application.router.add_post("/auth/recovery/verify", password_recovery_verify)
    application.router.add_post("/auth/recovery/password", password_recovery_set_password)
    application.router.add_post("/api/1c/auth/email", one_c_email_login)
    application.router.add_get("/auth/1c/exchange/{ticket}", one_c_exchange)
    application.router.add_post("/auth/request", request_code)
    application.router.add_post("/auth/verify", verify_code)
    application.router.add_get("/register", registration_page)
    application.router.add_post("/register", registration_submit)
    application.router.add_get("/logout", logout)
    application.router.add_get("/", dashboard)
    application.router.add_get("/api/version", application_version)
    application.router.add_post("/api/presence/heartbeat", presence_heartbeat)
    application.router.add_get("/api/presence/statuses", presence_statuses)
    application.router.add_post("/api/agent/heartbeat", agent_heartbeat)
    application.router.add_post("/api/agent/work-state", agent_work_state_update)
    application.router.add_post("/api/work-state", web_work_state_update)
    application.router.add_get("/api/work-state/current", web_work_state_current)
    application.router.add_get("/organizations", organizations)
    application.router.add_get("/organizations/create", organization_create_page)
    application.router.add_post("/organizations/create", organization_create_submit)
    application.router.add_get("/organizations/{id:\\d+}", organization_card)
    application.router.add_get("/organizations/{id:\\d+}/email-domains", organization_email_domains_page)
    application.router.add_post("/organizations/{id:\\d+}/email-domains", organization_email_domains_update)
    application.router.add_get("/organizations/{id:\\d+}/rename", organization_rename_page)
    application.router.add_post("/organizations/{id:\\d+}/rename", organization_rename_update)
    application.router.add_post("/organizations/{id:\\d+}/lifecycle", organization_lifecycle)
    application.router.add_get("/organizations/{id:\\d+}/registry", organization_registry_page)
    application.router.add_post("/organizations/{id:\\d+}/registry", organization_registry_fill)
    application.router.add_post("/organizations/{id:\\d+}/registry/update", organization_registry_update)
    application.router.add_get("/organizations/{id:\\d+}/audit", organization_audit_page)
    application.router.add_get("/organizations/{id:\\d+}/structure", organization_structure)
    application.router.add_get("/holdings", holdings_page)
    application.router.add_get("/holdings/create", holding_create_page)
    application.router.add_post("/holdings/create", holding_create_submit)
    application.router.add_get("/holdings/{id:\\d+}", holding_card)
    application.router.add_get("/holdings/{id:\\d+}/rename", holding_rename_page)
    application.router.add_post("/holdings/{id:\\d+}/rename", holding_rename_update)
    application.router.add_post("/holdings/{id:\\d+}/lifecycle", holding_lifecycle)
    application.router.add_get("/holdings/{id:\\d+}/companies", holding_companies)
    application.router.add_get("/holdings/{id:\\d+}/admins", holding_admins)
    application.router.add_get("/holdings/{id:\\d+}/audit", holding_audit_page)
    application.router.add_get("/employees", employees_page)
    application.router.add_get("/employees/{id:\\d+}", employee_card)
    application.router.add_post("/employees/{id:\\d+}/work-tracking", employee_tracking_update)
    application.router.add_post("/employees/{id:\\d+}/schedule", employee_schedule_update)
    application.router.add_get("/tickets", tickets_page)
    application.router.add_get("/tickets/{id:\\d+}", ticket_card)
    application.router.add_get("/reports", reports_page)
    application.router.add_get("/access", access_page)
    application.router.add_get("/access/2fa-reset", two_factor_reset_page)
    application.router.add_post("/access/2fa-reset", two_factor_reset_submit)
    application.router.add_get("/access/assign", access_assign_page)
    application.router.add_post("/access/assign", access_assign_submit)
    application.router.add_post("/access/assignments/{id:\\d+}/revoke", access_assignment_revoke)
    application.router.add_get("/access/audit", access_audit_page)
    application.router.add_get("/access/roles", access_roles_page)
    application.router.add_get("/access/permissions", access_permissions_page)
    application.router.add_get("/admin/mail", mail_settings_page)
    application.router.add_post("/admin/mail", mail_settings_update)
    application.router.add_get("/admin/invitations/new", invitation_page)
    application.router.add_post("/admin/invitations", invitation_create)
    application.router.add_get("/profile", profile_page)
    application.router.add_get("/profile/email", profile_email_page)
    application.router.add_post("/profile/email/request", profile_email_request)
    application.router.add_post("/profile/email/confirm", profile_email_confirm)
    application.router.add_get("/language", language_page)
    application.router.add_get("/language/cleanup", language_cleanup_page)
    application.router.add_post("/language/cleanup", language_cleanup_submit)
    application.router.add_post("/language/install", language_install_start)
    application.router.add_get("/language/jobs/{job_id}", language_install_status)
    return application
