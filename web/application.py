import hashlib
import html
import secrets
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiohttp
from aiohttp import web
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database.db import AsyncSessionLocal
from app.models.account import Account
from app.models.account_organizational_unit_membership import (
    AccountOrganizationalUnitMembership,
)
from app.models.holding import Holding
from app.models.enums import ScopeType, TicketStatus, UserRole
from app.models.message import Message
from app.models.organization import Organization
from app.models.organizational_unit import OrganizationalUnit
from app.models.role_assignment import RoleAssignment
from app.models.ticket import Ticket
from app.security.authorization import AuthorizationService
from app.security.business_unit_access import BusinessUnitAccessService
from app.security.holding_access import HoldingAccessService
from app.security.organization_access import OrganizationAccessService
from app.security.permissions import Permission
from app.services.employee_service import EmployeeService


STATIC_ROOT = Path(__file__).resolve().parent / "static"
SESSION_COOKIE = "supportbot_session"
LOGIN_TTL = timedelta(minutes=10)
SESSION_TTL = timedelta(hours=12)


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


LOGIN_CHALLENGES: dict[str, LoginChallenge] = {}
WEB_SESSIONS: dict[str, WebSession] = {}


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
        return await db.scalar(
            select(Account).where(
                Account.id == session.account_id,
                Account.is_active.is_(True),
                Account.registered.is_(True),
            )
        )


@web.middleware
async def account_middleware(request: web.Request, handler):
    request["account"] = await current_account(request)
    public = request.path in {
        "/login",
        "/auth/request",
        "/auth/verify",
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


async def login_page(request: web.Request) -> web.Response:
    if request["account"]:
        raise web.HTTPFound("/")
    content = """<section class="login-card glass"><div class="login-logo">S</div>
<h2>Вход в кабинет</h2><p>Введите Telegram ID. Одноразовый код придёт от бота.</p>
<form method="post" action="/auth/request"><label>Telegram ID</label>
<input name="telegram_id" inputmode="numeric" required autocomplete="username">
<button type="submit">Получить код</button></form></section>"""
    return page("Вход", content)


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
    token = secrets.token_urlsafe(32)
    WEB_SESSIONS[token] = WebSession(
        account_id=challenge.account_id,
        csrf_token=secrets.token_urlsafe(24),
        expires_at=now() + SESSION_TTL,
    )
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
    async with AsyncSessionLocal() as db:
        values = await OrganizationAccessService(db).list_visible_organizations(account)
    if query:
        digits = "".join(filter(str.isdigit, query))
        values = [item for item in values if query.casefold() in item.name.casefold() or (digits and digits in (item.inn or ""))]
    items = [
        f'<a class="data-card glass" href="/organizations/{item.id}"><div class="card-icon">🏢</div>'
        f'<div><h3>{esc(item.name)}</h3><p>ИНН {esc(item.inn or "не указан")} · {"Активна" if item.is_active else "Архив"}</p></div></a>'
        for item in values[:100]
    ]
    return page("Организации", search_form("/organizations", query, "ИНН или наименование") + cards(items), account=account, active="organizations")


@authenticated
async def organization_card(request: web.Request, account: Account) -> web.Response:
    organization_id = int(request.match_info["id"])
    async with AsyncSessionLocal() as db:
        access = OrganizationAccessService(db)
        if not await access.can_access_organization(account, organization_id):
            return error_page("Организация недоступна.", status=403, account=account)
        organization = await db.scalar(select(Organization).where(Organization.id == organization_id))
        holdings = list(await db.scalars(select(Holding).where(Holding.organization_id == organization_id).order_by(Holding.name)))
        units = list(await db.scalars(select(OrganizationalUnit).where(OrganizationalUnit.organization_id == organization_id).order_by(OrganizationalUnit.name)))
    content = f'''<section class="detail-grid"><article class="panel glass"><h2>{esc(organization.name)}</h2>
<dl><dt>ID 1С</dt><dd>{esc(organization.external_id)}</dd><dt>Тип</dt><dd>{esc(organization.organization_type.value)}</dd>
<dt>ИНН</dt><dd>{esc(organization.inn or "—")}</dd><dt>КПП</dt><dd>{esc(organization.kpp or "—")}</dd>
<dt>ОГРН</dt><dd>{esc(organization.ogrn or "—")}</dd><dt>Юридический адрес</dt><dd>{esc(organization.legal_address or "—")}</dd></dl></article>
<article class="panel glass"><h2>Подразделения</h2>{''.join(f'<div class="list-row">🏗️ {esc(unit.name)}</div>' for unit in units) or '<p>Нет подразделений</p>'}</article>
<article class="panel glass"><h2>Холдинги</h2>{''.join(f'<a class="list-row" href="/holdings/{holding.id}">🏛️ {esc(holding.name)}</a>' for holding in holdings) or '<p>Нет холдингов</p>'}</article></section>'''
    return page("Карточка организации", content, account=account, active="organizations")


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
    return page("Холдинги", search_form("/holdings", request.query.get("q", ""), "Название холдинга или организации") + cards(items), account=account, active="holdings")


@authenticated
async def holding_card(request: web.Request, account: Account) -> web.Response:
    holding_id = int(request.match_info["id"])
    async with AsyncSessionLocal() as db:
        access = HoldingAccessService(db)
        if not await access.can_access_holding(account, holding_id):
            return error_page("Холдинг недоступен.", status=403, account=account)
        item = await db.scalar(select(Holding).where(Holding.id == holding_id).options(selectinload(Holding.organization)))
    content = f'<section class="panel glass"><div class="hero-icon">🏛️</div><h2>{esc(item.name)}</h2><dl><dt>Организация</dt><dd><a href="/organizations/{item.organization_id}">{esc(item.organization.name)}</a></dd><dt>Статус</dt><dd>{"Активен" if item.is_active else "В архиве"}</dd><dt>Создан</dt><dd>{esc(item.created_at.strftime("%d.%m.%Y"))}</dd></dl></section>'
    return page("Карточка холдинга", content, account=account, active="holdings")


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
            conditions = [Account.full_name.ilike(f"%{query}%")]
            if query.isdigit():
                conditions += [Account.id == int(query), Account.telegram_id == int(query)]
            statement = statement.where(or_(*conditions))
        if statement is not None:
            values = list(
                await db.scalars(
                    statement.distinct().order_by(Account.full_name).limit(100)
                )
            )
    items = [f'<a class="data-card glass" href="/employees/{item.id}"><div class="card-icon">👤</div><div><h3>{esc(item.full_name)}</h3><p>{esc(item.role.value)} · {"Активен" if item.is_active else "Отключён"}</p></div></a>' for item in values]
    return page("Сотрудники", search_form("/employees", query, "ФИО, ID или Telegram ID") + cards(items), account=account, active="employees")


@authenticated
async def employee_card(request: web.Request, account: Account) -> web.Response:
    if not await can(account, Permission.EMPLOYEE_VIEW):
        return error_page("Недостаточно прав.", status=403, account=account)
    async with AsyncSessionLocal() as db:
        item = await EmployeeService(db).get(int(request.match_info["id"]))
    if item is None:
        return error_page("Сотрудник не найден.", status=404, account=account)
    content = f'<section class="panel glass"><div class="hero-icon">👤</div><h2>{esc(item.full_name)}</h2><dl><dt>ID</dt><dd>{item.id}</dd><dt>Telegram ID</dt><dd>{esc(item.telegram_id)}</dd><dt>Роль</dt><dd>{esc(item.role.value)}</dd><dt>Язык</dt><dd>{esc(item.language)}</dd><dt>Статус</dt><dd>{"Активен" if item.is_active else "Отключён"}</dd></dl></section>'
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
async def access_page(request: web.Request, account: Account) -> web.Response:
    if not await can(account, Permission.ROLE_ASSIGN):
        return error_page("Недостаточно прав.", status=403, account=account)
    async with AsyncSessionLocal() as db:
        values = list(await db.scalars(select(RoleAssignment).where(RoleAssignment.is_active.is_(True)).options(selectinload(RoleAssignment.account), selectinload(RoleAssignment.role)).order_by(RoleAssignment.created_at.desc()).limit(100)))
    rows = ''.join(f'<tr><td>{item.id}</td><td>{esc(item.account.full_name)}</td><td>{esc(item.role.name)}</td><td>{esc(item.scope_type.value)}</td><td>{esc(item.scope_id or "Вся платформа")}</td></tr>' for item in values)
    return page("Доступы", f'<section class="table-wrap glass"><table><thead><tr><th>ID</th><th>Сотрудник</th><th>Роль</th><th>Область</th><th>Объект</th></tr></thead><tbody>{rows}</tbody></table></section>', account=account, active="access")


@authenticated
async def profile_page(request: web.Request, account: Account) -> web.Response:
    content = f'<section class="panel glass"><div class="hero-icon">👤</div><h2>{esc(account.full_name)}</h2><dl><dt>ID</dt><dd>{account.id}</dd><dt>Telegram ID</dt><dd>{esc(account.telegram_id)}</dd><dt>Роль</dt><dd>{esc(account.role.value)}</dd><dt>Язык</dt><dd>{esc(account.language)}</dd></dl></section>'
    return page("Профиль", content, account=account, active="profile")


@authenticated
async def language_page(request: web.Request, account: Account) -> web.Response:
    token = request.cookies.get(SESSION_COOKIE, "")
    session = WEB_SESSIONS[token]
    options = [("ru", "Русский"), ("en", "English")]
    content = '<section class="panel glass"><h2>Язык интерфейса</h2><form method="post" action="/language">' + f'<input type="hidden" name="csrf" value="{esc(session.csrf_token)}">' + ''.join(f'<label class="radio"><input type="radio" name="language" value="{code}" {"checked" if account.language == code else ""}><span>{label}</span></label>' for code, label in options) + '<button class="button" type="submit">Сохранить</button></form></section>'
    return page("Language", content, account=account, active="language")


@authenticated
async def language_update(request: web.Request, account: Account) -> web.Response:
    form = await request.post()
    token = request.cookies.get(SESSION_COOKIE, "")
    session = WEB_SESSIONS.get(token)
    if session is None or not secrets.compare_digest(str(form.get("csrf", "")), session.csrf_token):
        return error_page("Проверка безопасности не пройдена.", status=403, account=account)
    language = str(form.get("language", ""))
    if language not in {"ru", "en"}:
        return error_page("Язык не поддерживается.", account=account)
    async with AsyncSessionLocal() as db:
        stored = await db.get(Account, account.id)
        stored.language = language
        await db.commit()
    raise web.HTTPFound("/language")


def create_application() -> web.Application:
    application = web.Application(
        middlewares=[account_middleware],
        client_max_size=1024 * 1024,
    )
    application.router.add_static("/static/", STATIC_ROOT)
    application.router.add_get("/styles.css", lambda _: web.FileResponse(STATIC_ROOT / "styles.css"))
    application.router.add_get("/app.js", lambda _: web.FileResponse(STATIC_ROOT / "app.js"))
    application.router.add_get("/login", login_page)
    application.router.add_post("/auth/request", request_code)
    application.router.add_post("/auth/verify", verify_code)
    application.router.add_get("/logout", logout)
    application.router.add_get("/", dashboard)
    application.router.add_get("/organizations", organizations)
    application.router.add_get("/organizations/{id:\\d+}", organization_card)
    application.router.add_get("/holdings", holdings_page)
    application.router.add_get("/holdings/{id:\\d+}", holding_card)
    application.router.add_get("/employees", employees_page)
    application.router.add_get("/employees/{id:\\d+}", employee_card)
    application.router.add_get("/tickets", tickets_page)
    application.router.add_get("/tickets/{id:\\d+}", ticket_card)
    application.router.add_get("/reports", reports_page)
    application.router.add_get("/access", access_page)
    application.router.add_get("/profile", profile_page)
    application.router.add_get("/language", language_page)
    application.router.add_post("/language", language_update)
    return application
