from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import ScopeType


@dataclass(frozen=True, slots=True)
class AccessScope:
    """
    Область, в которой проверяется или назначается доступ.

    PLATFORM не имеет числового идентификатора.
    Остальные scope требуют положительный scope_id.
    """

    scope_type: ScopeType
    scope_id: int | None = None

    def __post_init__(self) -> None:
        if self.scope_type == ScopeType.PLATFORM:
            if self.scope_id is not None:
                raise ValueError(
                    "PLATFORM scope не должен содержать scope_id."
                )
            return

        if self.scope_id is None:
            raise ValueError(
                f"{self.scope_type.value} scope требует scope_id."
            )

        if self.scope_id <= 0:
            raise ValueError(
                "scope_id должен быть положительным числом."
            )

    @classmethod
    def platform(cls) -> AccessScope:
        return cls(
            scope_type=ScopeType.PLATFORM,
            scope_id=None,
        )

    @classmethod
    def organization(cls, organization_id: int) -> AccessScope:
        return cls(
            scope_type=ScopeType.ORGANIZATION,
            scope_id=organization_id,
        )

    @classmethod
    def holding(cls, holding_id: int) -> AccessScope:
        return cls(
            scope_type=ScopeType.HOLDING,
            scope_id=holding_id,
        )

    @classmethod
    def business_unit(cls, business_unit_id: int) -> AccessScope:
        return cls(
            scope_type=ScopeType.BUSINESS_UNIT,
            scope_id=business_unit_id,
        )

    @classmethod
    def support_contract(
        cls,
        contract_id: int,
    ) -> AccessScope:
        return cls(
            scope_type=ScopeType.SUPPORT_CONTRACT,
            scope_id=contract_id,
        )

    @classmethod
    def support_queue(cls, queue_id: int) -> AccessScope:
        return cls(
            scope_type=ScopeType.SUPPORT_QUEUE,
            scope_id=queue_id,
        )

    @classmethod
    def ticket(cls, ticket_id: int) -> AccessScope:
        return cls(
            scope_type=ScopeType.TICKET,
            scope_id=ticket_id,
        )

    @property
    def is_platform(self) -> bool:
        return self.scope_type == ScopeType.PLATFORM

    def as_key(self) -> tuple[str, int | None]:
        return self.scope_type.value, self.scope_id

    def __str__(self) -> str:
        if self.is_platform:
            return self.scope_type.value

        return f"{self.scope_type.value}:{self.scope_id}"
