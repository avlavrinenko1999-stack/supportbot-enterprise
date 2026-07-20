import asyncio
import hashlib
import html
import os
import secrets
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import aiohttp
from aiohttp import web
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database.db import AsyncSessionLocal
from app.models.account import Account
from app.models.access_audit_event import AccessAuditEvent
from app.models.account_organizational_unit_membership import (
    AccountOrganizationalUnitMembership,
)
from app.models.holding import Holding
from app.models.enums import (
    InviteRole,
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
from app.services.role_assignment_service import RoleAssignmentService
from app.services.web_identity_service import WebIdentityService
from app.services.vidal_service import VidalService
from app.services.organization_audit_service import OrganizationAuditService
from app.services.organization_registry_service import OrganizationRegistryService
from app.services.organization_service import OrganizationService
from app.keyboards.organization import organization_type_label


STATIC_ROOT = Path(__file__).resolve().parent / "static"
SESSION_COOKIE = "supportbot_session"
LOGIN_TTL = timedelta(minutes=10)
SESSION_TTL = timedelta(hours=12)
WEB_PUBLIC_URL = os.getenv("WEB_PUBLIC_URL", "http://127.0.0.1:8080").rstrip("/")


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


LOGIN_CHALLENGES: dict[str, LoginChallenge] = {}
WEB_SESSIONS: dict[str, WebSession] = {}
LANGUAGE_INSTALL_JOBS: dict[str, LanguageInstallJob] = {}
LANGUAGE_INSTALL_TASKS: set[asyncio.Task] = set()


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def now() -> datetime:
    return datetime.now(timezone.utc)


def page(
    title: str,
    content: str,
    *,
    account: Account | None = None,
    active: str = "",
) -> web.Response:
    navigation = ""
    if account is not None:
        items = [
            ("organizations", "🏢", "Организации"),
            ("holdings", "🏛️", "Холдинги"),
            ("employees", "👥", "Сотрудники"),
            ("tickets", "🎫", "Тикеты"),
            ("reports", "📊", "Отчёты"),
            ("access", "🔐", "Доступы"),
            ("profile", "👤", "Профиль"),
            ("language", "🌐", "Language"),
        ]
        if getattr(account, "web_platform_admin", False):
            items.insert(6, ("vidal", "💊", "Vidal"))
        links = "".join(
            f'<a class="nav-item {"active" if key == active else ""}" '
            f'href="/{key}"><span>{icon}</span>{label}</a>'
            for key, icon, label in items
        )
        navigation = (
            '<aside class="sidebar glass"><a class="logo" href="/">S</a>'
            f'<nav>{links}</nav><a class="nav-item" href="/logout">'
            "<span>↪</span>Выйти</a></aside>"
        )

    shell_class = "app-shell" if account else "auth-shell"
    account_line = (
        f'<div class="account-chip">{esc(account.full_name)}</div>'
        if account
        else ""
    )
    document = f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#44474c">
<title>{esc(title)} · SupportBot Enterprise</title>
<link rel="stylesheet" href="/styles.css"></head>
<body><div class="wallpaper"><span class="orb orb-one"></span>
<span class="orb orb-two"></span><span class="orb orb-three"></span></div>
<div class="{shell_class}">{navigation}<main class="workspace">
<header class="workspace-header"><div><div class="eyebrow">SupportBot Enterprise</div>
<h1>{esc(title)}</h1></div>{account_line}</header>{content}</main></div></body></html>"""
    return web.Response(text=document, content_type="text/html", charset="utf-8")


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
        return None
    async with AsyncSessionLocal() as db:
        account = await db.scalar(
            select(Account).where(
                Account.id == session.account_id,
                Account.is_active.is_(True),
                Account.registered.is_(True),
            )
        )
        if account is not None:
            account.web_platform_admin = await is_platform_admin(db, account)
        return account


@web.middleware
async def account_middleware(request: web.Request, handler):
    request["account"] = await current_account(request)
    public = request.path in {
        "/login",
        "/auth/email",
        "/auth/request",
        "/auth/verify",
        "/register",
        "/styles.css",
        "/app.js",
    }
    public = public or request.path.startswith("/static/")
    if request["account"] is None and not public:
        raise web.HTTPFound("/login")
    return await handler(request)


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


async def is_platform_admin(db, account: Account) -> bool:
    current_time = now()
    assignment_count = await db.scalar(
        select(func.count(RoleAssignment.id)).where(
            RoleAssignment.account_id == account.id,
            RoleAssignment.is_active.is_(True),
            RoleAssignment.revoked_at.is_(None),
        )
    ) or 0
    if assignment_count == 0:
        return account.role == UserRole.ADMIN
    platform_admin_id = await db.scalar(
        select(RoleAssignment.id)
        .join(Role, Role.id == RoleAssignment.role_id)
        .where(
            RoleAssignment.account_id == account.id,
            RoleAssignment.scope_type == ScopeType.PLATFORM,
            RoleAssignment.scope_id.is_(None),
            RoleAssignment.is_active.is_(True),
            RoleAssignment.revoked_at.is_(None),
            Role.is_active.is_(True),
            Role.code == "platform_admin",
            or_(RoleAssignment.valid_from.is_(None), RoleAssignment.valid_from <= current_time),
            or_(RoleAssignment.valid_to.is_(None), RoleAssignment.valid_to > current_time),
        )
    )
    return platform_admin_id is not None


async def login_page(request: web.Request) -> web.Response:
    if request["account"]:
        raise web.HTTPFound("/")
    content = """<section class="login-card glass"><div class="login-logo">S</div>
<h2>Вход в кабинет</h2><p>Используйте email и пароль или получите код в Telegram.</p>
<form method="post" action="/auth/email"><label>Email</label>
<input type="email" name="email" required autocomplete="username">
<label>Пароль</label><input type="password" name="password" required autocomplete="current-password">
<button type="submit">Войти</button></form><div class="form-divider">или</div>
<form method="post" action="/auth/request"><label>Telegram ID</label>
<input name="telegram_id" inputmode="numeric" required>
<button type="submit" class="secondary">Получить код в Telegram</button></form></section>"""
    return page("Вход", content)


def establish_session(account_id: int) -> tuple[str, WebSession]:
    token = secrets.token_urlsafe(32)
    session = WebSession(
        account_id=account_id,
        csrf_token=secrets.token_urlsafe(24),
        expires_at=now() + SESSION_TTL,
    )
    WEB_SESSIONS[token] = session
    return token, session


def login_response(account_id: int) -> web.Response:
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
    return login_response(account.id)


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
<form method="post" action="/auth/verify">
<input type="hidden" name="challenge" value="{esc(challenge_id)}">
<label>Код подтверждения</label><input name="code" inputmode="numeric" maxlength="6" required autofocus>
<button type="submit">Войти</button></form></section>"""
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
    return login_response(challenge.account_id)


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
    return login_response(account_id)


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
    response = web.HTTPFound("/login")
    response.del_cookie(SESSION_COOKIE, path="/")
    return response


@authenticated
async def dashboard(request: web.Request, account: Account) -> web.Response:
    sections = [
        ("organizations", "🏢", "Организации", Permission.ORGANIZATION_VIEW),
        ("holdings", "🏛️", "Холдинги", Permission.HOLDING_VIEW),
        ("employees", "👥", "Сотрудники", Permission.EMPLOYEE_VIEW),
        ("tickets", "🎫", "Тикеты", Permission.TICKET_VIEW),
        ("reports", "📊", "Отчёты", Permission.REPORT_VIEW),
        ("access", "🔐", "Доступы", Permission.ROLE_ASSIGN),
        ("profile", "👤", "Профиль", None),
        ("language", "🌐", "Language", None),
    ]
    if getattr(account, "web_platform_admin", False):
        sections.insert(6, ("vidal", "💊", "Справочник Vidal", None))
    allowed = []
    for path, icon, label, permission in sections:
        if permission is None or await can(account, permission):
            allowed.append(
                f'<a class="launch-app" href="/{path}"><span class="app-icon">'
                f'{icon}</span><span>{label}</span></a>'
            )
    return page(
        "Главная",
        f'<section class="launch-grid">{"".join(allowed)}</section>',
        account=account,
    )


@authenticated
async def organizations(request: web.Request, account: Account) -> web.Response:
    if not await can(account, Permission.ORGANIZATION_VIEW):
        return error_page("Недостаточно прав.", status=403, account=account)
    query = request.query.get("q", "").strip()

    search = search_form(
        "/organizations",
        query,
        "ИНН или часть наименования",
    )
    if not query:
        return page(
            "Организации",
            search
            + '<section class="empty glass">Введите ИНН или часть '
            "наименования организации.</section>",
            account=account,
            active="organizations",
        )
    if len(query) < 2:
        return page(
            "Организации",
            search
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
        search + cards(items, "Совпадений среди доступных организаций нет"),
        account=account,
        active="organizations",
    )


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
    content = f'''<section class="organization-layout"><article class="organization-card panel glass">
<div class="organization-heading"><div class="hero-icon">🏢</div><div><span class="status-pill">{"активна" if organization.is_active else "отключена"}</span><h2>{esc(organization.name)}</h2><p>{esc(organization_type_label(organization.organization_type))}</p></div></div>
<div class="card-section"><h3>Организация</h3><dl><dt>ID</dt><dd>{esc(organization.external_id)}</dd><dt>Название</dt><dd>{esc(organization.name)}</dd><dt>Тип</dt><dd>{esc(organization_type_label(organization.organization_type))}</dd><dt>Статус</dt><dd>{"активна" if organization.is_active else "отключена"}</dd><dt>Родитель</dt><dd>{esc(organization.parent.name if organization.parent else "нет")}</dd></dl></div>
<div class="card-section"><h3>Юридические данные</h3><dl><dt>Название</dt><dd>{esc(organization.legal_name or "не заполнено")}</dd><dt>ИНН</dt><dd>{esc(organization.inn or "не заполнен")}</dd><dt>КПП</dt><dd>{esc(organization.kpp or "не заполнен")}</dd><dt>ОГРН</dt><dd>{esc(organization.ogrn or "не заполнен")}</dd><dt>Юр. статус</dt><dd>{esc(organization.legal_status or "не заполнен")}</dd><dt>Синхронизация</dt><dd>{esc(synchronized)}</dd></dl></div>
<div class="organization-counters"><span>Дочерних организаций <b>{len(organization.children)}</b></span><span>Холдингов <b>{len(holdings)}</b></span></div></article>
<aside class="organization-actions glass"><h3>Действия</h3>{''.join(action_items)}</aside></section>
<section id="units" class="panel glass content-section"><h2>Подразделения</h2>{''.join(f'<div class="list-row">🏗️ {esc(unit.name)}</div>' for unit in units) or '<p>Нет подразделений</p>'}</section>
<article class="panel glass content-section"><h2>Холдинги</h2>{''.join(f'<a class="list-row" href="/holdings/{holding.id}">🏛️ {esc(holding.name)}</a>' for holding in holdings) or '<p>Нет холдингов</p>'}</article>'''
    return page("Карточка организации", content, account=account, active="organizations")


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
    items = [f'<a class="data-card glass" href="/employees/{item.id}"><div class="card-icon">👤</div><div><h3>{esc(item.full_name)}</h3><p>{esc(item.role.value)} · {"Активен" if item.is_active else "Отключён"}</p></div></a>' for item in values]
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
    content = f'<div class="action-bar"><a class="button secondary-link" href="/employees">⬅️ Сотрудники</a><a class="button secondary-link" href="/">⬅️ Назад</a></div><section class="panel glass"><div class="hero-icon">👤</div><h2>{esc(item.full_name)}</h2><dl><dt>ID</dt><dd>{item.id}</dd><dt>Email</dt><dd>{esc(item.email or "—")}</dd><dt>Telegram ID</dt><dd>{esc(item.telegram_id or "—")}</dd><dt>Роль</dt><dd>{esc(get_role_name(item.role))}</dd><dt>Язык</dt><dd>{esc(item.language)}</dd><dt>Статус</dt><dd>{"Активен" if item.is_active else "Отключён"}</dd></dl></section>'
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


async def require_platform_admin(account: Account) -> bool:
    async with AsyncSessionLocal() as db:
        return await is_platform_admin(db, account)


@authenticated
async def vidal_page(request: web.Request, account: Account) -> web.Response:
    if not await require_platform_admin(account):
        return error_page("Справочник Vidal доступен только администратору платформы.", status=403, account=account)
    query = request.query.get("q", "").strip()
    search = search_form("/vidal/search", query, "Название препарата, действующее вещество или АТХ-код")
    sections = '''<section class="data-grid vidal-sections">
<a class="data-card glass" href="https://www.vidal.ru/drugs" target="_blank" rel="noopener noreferrer"><div class="card-icon">💊</div><div><h3>Препараты</h3><p>Официальный справочник лекарственных средств</p></div></a>
<a class="data-card glass" href="https://www.vidal.ru/drugs/molecules" target="_blank" rel="noopener noreferrer"><div class="card-icon">🧬</div><div><h3>Активные вещества</h3><p>Поиск по действующему веществу</p></div></a>
<a class="data-card glass" href="https://www.vidal.ru/drugs/atc" target="_blank" rel="noopener noreferrer"><div class="card-icon">🧪</div><div><h3>АТХ</h3><p>Анатомо-терапевтическая классификация</p></div></a>
<a class="data-card glass" href="https://www.vidal.ru/drugs/interaction/new" target="_blank" rel="noopener noreferrer"><div class="card-icon">⚕️</div><div><h3>Взаимодействия</h3><p>Проверка взаимодействия препаратов</p></div></a></section>'''
    notice = '<section class="panel glass content-section"><h2>Важная информация</h2><p>Поиск открывает актуальные данные официального справочника Vidal. Информация предназначена для специалистов и не заменяет консультацию врача.</p></section>'
    return page("Справочник Vidal", search + sections + notice, account=account, active="vidal")


@authenticated
async def vidal_search(request: web.Request, account: Account) -> web.Response:
    if not await require_platform_admin(account):
        return error_page("Справочник Vidal доступен только администратору платформы.", status=403, account=account)
    query = request.query.get("q", "").strip()
    if len(query) < 2:
        return error_page("Введите не менее двух символов для поиска.", account=account)
    try:
        results = await VidalService.search(query)
    except (aiohttp.ClientError, TimeoutError):
        return error_page("Справочник Vidal временно недоступен. Повторите поиск позже.", status=502, account=account)
    items = [f'''<article class="data-card glass vidal-result"><div class="card-icon">💊</div><div><h3>{esc(item.name)}</h3><p>{esc(item.release_form or "Форма выпуска не указана")}</p><p>{esc(item.company or "Производитель не указан")}</p><p>{esc(item.registration or "Регистрационные сведения не указаны")}</p><span class="status-pill">{esc(item.availability or "Статус отпуска не указан")}</span><div><a class="button secondary-link" href="{esc(item.url)}" target="_blank" rel="noopener noreferrer">Официальная карточка Vidal ↗</a></div></div></article>''' for item in results]
    content = '<div class="action-bar"><a class="button secondary-link" href="/vidal">⬅️ Справочник Vidal</a></div>' + search_form("/vidal/search", query, "Название препарата") + cards(items, "Препараты не найдены")
    return page(f"Vidal · {query}", content, account=account, active="vidal")


@authenticated
async def access_page(request: web.Request, account: Account) -> web.Response:
    if not await can(account, Permission.ROLE_ASSIGN):
        return error_page("Недостаточно прав.", status=403, account=account)
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
        '<a class="button secondary-link" href="/admin/mail">Настройки почты</a></div>'
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
    content = f'<section class="panel glass"><div class="hero-icon">👤</div><h2>{esc(account.full_name)}</h2><dl><dt>ID</dt><dd>{account.id}</dd><dt>Email</dt><dd>{esc(account.email or "—")}</dd><dt>Telegram ID</dt><dd>{esc(account.telegram_id or "—")}</dd><dt>Роль</dt><dd>{esc(get_role_name(account.role))}</dd><dt>Язык</dt><dd>{esc(account.language)}</dd><dt>Активен</dt><dd>{"да" if account.is_active else "нет"}</dd><dt>Зарегистрирован</dt><dd>{"да" if account.registered else "нет"}</dd></dl><div class="card-section"><h3>Разрешения</h3><ul>{permissions_html}</ul></div></section>'
    return page("Профиль", content, account=account, active="profile")


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
    content = f'''<section class="panel glass"><h2>🌐 Language</h2><p>Введите любой язык, например: English, Русский, Deutsch или Chinese Simplified.</p><form class="search glass" method="get" action="/language"><input name="q" value="{esc(query)}" placeholder="Type your language" required><button type="submit">Найти</button></form></section><p class="language-hint">{esc(message)}</p><section class="data-grid">{cards_html}</section>'''
    return page("Language", content, account=account, active="language")


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
        middlewares=[account_middleware],
        client_max_size=1024 * 1024,
    )
    application.router.add_static("/static/", STATIC_ROOT)
    application.router.add_get("/styles.css", lambda _: web.FileResponse(STATIC_ROOT / "styles.css"))
    application.router.add_get("/app.js", lambda _: web.FileResponse(STATIC_ROOT / "app.js"))
    application.router.add_get("/login", login_page)
    application.router.add_post("/auth/email", email_login)
    application.router.add_post("/auth/request", request_code)
    application.router.add_post("/auth/verify", verify_code)
    application.router.add_get("/register", registration_page)
    application.router.add_post("/register", registration_submit)
    application.router.add_get("/logout", logout)
    application.router.add_get("/", dashboard)
    application.router.add_get("/organizations", organizations)
    application.router.add_get("/organizations/{id:\\d+}", organization_card)
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
    application.router.add_get("/tickets", tickets_page)
    application.router.add_get("/tickets/{id:\\d+}", ticket_card)
    application.router.add_get("/reports", reports_page)
    application.router.add_get("/vidal", vidal_page)
    application.router.add_get("/vidal/search", vidal_search)
    application.router.add_get("/access", access_page)
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
    application.router.add_get("/language", language_page)
    application.router.add_post("/language/install", language_install_start)
    application.router.add_get("/language/jobs/{job_id}", language_install_status)
    return application
