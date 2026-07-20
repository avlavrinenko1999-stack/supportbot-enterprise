from unittest.mock import AsyncMock, MagicMock
from pathlib import Path

import pytest

from app.models.enums import ScopeType
from app.security.scope_resolver import ScopeResolver


@pytest.mark.asyncio
async def test_organization_scope_inherits_from_ancestors() -> None:
    session = MagicMock()
    session.scalars = AsyncMock(
        return_value=[30, 20, 10]
    )

    scopes = await ScopeResolver(
        session
    )._organization_lineage(30)

    assert [
        (scope.scope_type, scope.scope_id)
        for scope in scopes
    ] == [
        (ScopeType.ORGANIZATION, 10),
        (ScopeType.ORGANIZATION, 20),
        (ScopeType.ORGANIZATION, 30),
    ]


def test_mutating_fsm_steps_repeat_permission_checks() -> None:
    from app.handlers.admin.organization import create, edit

    create_source = Path(create.__file__).read_text(
        encoding="utf-8"
    )
    edit_source = Path(edit.__file__).read_text(
        encoding="utf-8"
    )

    assert "target_scope" in create_source
    assert "AuthorizationService.can_async" in create_source
    assert "@router.message(OrganizationState.rename_name)\n@require_permission" in (
        edit_source
    )
