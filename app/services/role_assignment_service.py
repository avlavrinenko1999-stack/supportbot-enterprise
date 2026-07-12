from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account import Account
from app.models.role import Role
from app.models.role_assignment import RoleAssignment
from app.security.access_scope import AccessScope


class RoleAssignmentService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def assign_role(
        self,
        *,
        account_id: int,
        role_code: str,
        scope: AccessScope,
        granted_by_account_id: int | None = None,
        grant_reason: str | None = None,
        valid_from: datetime | None = None,
        valid_to: datetime | None = None,
        commit: bool = True,
    ) -> RoleAssignment:
        self._validate_period(valid_from, valid_to)

        account = await self.session.get(Account, account_id)

        if account is None:
            raise ValueError("Аккаунт не найден.")

        role = await self.session.scalar(
            select(Role).where(
                Role.code == role_code,
                Role.is_active.is_(True),
            )
        )

        if role is None:
            raise ValueError(
                f"Активная роль {role_code!r} не найдена."
            )

        if granted_by_account_id is not None:
            grantor = await self.session.get(
                Account,
                granted_by_account_id,
            )

            if grantor is None:
                raise ValueError(
                    "Аккаунт, выдающий роль, не найден."
                )

        existing = await self.session.scalar(
            select(RoleAssignment).where(
                RoleAssignment.account_id == account_id,
                RoleAssignment.role_id == role.id,
                RoleAssignment.scope_type == scope.scope_type,
                RoleAssignment.scope_id == scope.scope_id,
                RoleAssignment.is_active.is_(True),
                RoleAssignment.revoked_at.is_(None),
            )
        )

        if existing is not None:
            return existing

        assignment = RoleAssignment(
            account_id=account_id,
            role_id=role.id,
            scope_type=scope.scope_type,
            scope_id=scope.scope_id,
            valid_from=valid_from,
            valid_to=valid_to,
            granted_by_account_id=granted_by_account_id,
            grant_reason=self._clean_reason(grant_reason),
            is_active=True,
        )

        self.session.add(assignment)

        if commit:
            await self.session.commit()
            await self.session.refresh(assignment)
        else:
            await self.session.flush()

        return assignment

    async def revoke_assignment(
        self,
        assignment_id: int,
        *,
        revoked_by_account_id: int | None = None,
        commit: bool = True,
    ) -> RoleAssignment:
        assignment = await self.session.get(
            RoleAssignment,
            assignment_id,
        )

        if assignment is None:
            raise ValueError("Назначение роли не найдено.")

        if revoked_by_account_id is not None:
            revoker = await self.session.get(
                Account,
                revoked_by_account_id,
            )

            if revoker is None:
                raise ValueError(
                    "Аккаунт, отзывающий роль, не найден."
                )

        if not assignment.is_active:
            return assignment

        assignment.is_active = False
        assignment.revoked_at = datetime.now(timezone.utc)
        assignment.revoked_by_account_id = (
            revoked_by_account_id
        )

        if commit:
            await self.session.commit()
            await self.session.refresh(assignment)
        else:
            await self.session.flush()

        return assignment

    async def list_active_assignments(
        self,
        account_id: int,
    ) -> list[RoleAssignment]:
        now = datetime.now(timezone.utc)

        return list(
            await self.session.scalars(
                select(RoleAssignment)
                .where(
                    RoleAssignment.account_id == account_id,
                    RoleAssignment.is_active.is_(True),
                    RoleAssignment.revoked_at.is_(None),
                    or_(
                        RoleAssignment.valid_from.is_(None),
                        RoleAssignment.valid_from <= now,
                    ),
                    or_(
                        RoleAssignment.valid_to.is_(None),
                        RoleAssignment.valid_to > now,
                    ),
                )
                .options(
                    selectinload(RoleAssignment.role)
                )
                .order_by(
                    RoleAssignment.scope_type,
                    RoleAssignment.scope_id,
                    RoleAssignment.id,
                )
            )
        )

    async def list_scope_assignments(
        self,
        scope: AccessScope,
    ) -> list[RoleAssignment]:
        return list(
            await self.session.scalars(
                select(RoleAssignment)
                .where(
                    RoleAssignment.scope_type
                    == scope.scope_type,
                    RoleAssignment.scope_id
                    == scope.scope_id,
                    RoleAssignment.is_active.is_(True),
                    RoleAssignment.revoked_at.is_(None),
                )
                .options(
                    selectinload(RoleAssignment.role),
                    selectinload(RoleAssignment.account),
                )
                .order_by(
                    RoleAssignment.role_id,
                    RoleAssignment.account_id,
                )
            )
        )

    @staticmethod
    def _validate_period(
        valid_from: datetime | None,
        valid_to: datetime | None,
    ) -> None:
        if (
            valid_from is not None
            and valid_to is not None
            and valid_to <= valid_from
        ):
            raise ValueError(
                "Дата окончания должна быть позже даты начала."
            )

    @staticmethod
    def _clean_reason(reason: str | None) -> str | None:
        clean_reason = (reason or "").strip()

        if not clean_reason:
            return None

        if len(clean_reason) > 1024:
            raise ValueError(
                "Причина назначения роли слишком длинная."
            )

        return clean_reason
