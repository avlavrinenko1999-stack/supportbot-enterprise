from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.enums import ScopeType
from app.models.holding import Holding
from app.models.organization import Organization
from app.security.access_scope import AccessScope


class ScopeResolutionError(ValueError):
    """Ошибка разрешения иерархии областей доступа."""


class ScopeResolver:
    """
    Преобразует целевой scope в список областей назначений,
    которые дают доступ к этому объекту.

    Текущая иерархия:

    PLATFORM
        └── ORGANIZATION
                └── HOLDING
                        └── COMPANY

    Для ещё не реализованных уровней используется PLATFORM
    и точное совпадение scope.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def resolve_assignment_scopes(
        self,
        target: AccessScope,
    ) -> tuple[AccessScope, ...]:
        if target.scope_type == ScopeType.PLATFORM:
            return (AccessScope.platform(),)

        if target.scope_type == ScopeType.ORGANIZATION:
            return await self._resolve_organization(target)

        if target.scope_type == ScopeType.HOLDING:
            return await self._resolve_holding(target)

        if target.scope_type == ScopeType.COMPANY:
            return await self._resolve_company(target)

        return (
            AccessScope.platform(),
            target,
        )

    async def _resolve_organization(
        self,
        target: AccessScope,
    ) -> tuple[AccessScope, ...]:
        organization_id = self._required_scope_id(target)

        organization = await self.session.get(
            Organization,
            organization_id,
        )

        if organization is None:
            raise ScopeResolutionError(
                "Организация области доступа не найдена."
            )

        return (
            AccessScope.platform(),
            target,
        )

    async def _resolve_holding(
        self,
        target: AccessScope,
    ) -> tuple[AccessScope, ...]:
        holding_id = self._required_scope_id(target)

        holding = await self.session.get(
            Holding,
            holding_id,
        )

        if holding is None:
            raise ScopeResolutionError(
                "Холдинг области доступа не найден."
            )

        return (
            AccessScope.platform(),
            AccessScope.organization(holding.organization_id),
            target,
        )

    async def _resolve_company(
        self,
        target: AccessScope,
    ) -> tuple[AccessScope, ...]:
        company_id = self._required_scope_id(target)

        company = await self.session.get(
            Company,
            company_id,
        )

        if company is None:
            raise ScopeResolutionError(
                "Компания области доступа не найдена."
            )

        scopes: list[AccessScope] = [
            AccessScope.platform(),
        ]

        effective_organization_id = company.organization_id

        if company.holding_id is not None:
            holding = await self.session.get(
                Holding,
                company.holding_id,
            )

            if holding is None:
                raise ScopeResolutionError(
                    "Холдинг компании не найден."
                )

            if (
                effective_organization_id is not None
                and effective_organization_id
                != holding.organization_id
            ):
                raise ScopeResolutionError(
                    "Компания и её холдинг принадлежат "
                    "разным организациям."
                )

            effective_organization_id = holding.organization_id

            scopes.append(
                AccessScope.holding(holding.id)
            )

        if effective_organization_id is not None:
            scopes.insert(
                1,
                AccessScope.organization(
                    effective_organization_id
                ),
            )

        scopes.append(target)

        return self._unique(scopes)

    @staticmethod
    def _required_scope_id(scope: AccessScope) -> int:
        if scope.scope_id is None:
            raise ScopeResolutionError(
                f"{scope.scope_type.value} требует scope_id."
            )

        return scope.scope_id

    @staticmethod
    def _unique(
        scopes: list[AccessScope],
    ) -> tuple[AccessScope, ...]:
        result: list[AccessScope] = []
        seen: set[tuple[str, int | None]] = set()

        for scope in scopes:
            key = scope.as_key()

            if key in seen:
                continue

            seen.add(key)
            result.append(scope)

        return tuple(result)
