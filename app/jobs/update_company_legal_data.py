from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
import os

from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.models.legal_entity import LegalEntity
from app.services.legal_entity_registry_service import (
    LegalEntityRegistryService,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RegistryJobConfig:
    batch_size: int
    request_delay_seconds: float
    retry_attempts: int
    retry_delay_seconds: float

    @classmethod
    def from_environment(cls) -> "RegistryJobConfig":
        return cls(
            batch_size=_positive_int(
                os.getenv(
                    "DADATA_SYNC_BATCH_SIZE",
                    "100",
                ),
                default=100,
                maximum=1000,
            ),
            request_delay_seconds=_non_negative_float(
                os.getenv(
                    "DADATA_SYNC_REQUEST_DELAY_SECONDS",
                    "1",
                ),
                default=1.0,
                maximum=60.0,
            ),
            retry_attempts=_positive_int(
                os.getenv(
                    "DADATA_SYNC_RETRY_ATTEMPTS",
                    "3",
                ),
                default=3,
                maximum=10,
            ),
            retry_delay_seconds=_non_negative_float(
                os.getenv(
                    "DADATA_SYNC_RETRY_DELAY_SECONDS",
                    "5",
                ),
                default=5.0,
                maximum=300.0,
            ),
        )


@dataclass
class RegistryJobResult:
    selected: int = 0
    updated: int = 0
    failed: int = 0
    skipped: int = 0

    @property
    def successful(self) -> bool:
        return self.failed == 0


def _positive_int(
    value: str | None,
    *,
    default: int,
    maximum: int,
) -> int:
    try:
        parsed = int(value or "")
    except ValueError:
        return default

    if parsed <= 0:
        return default

    return min(parsed, maximum)


def _non_negative_float(
    value: str | None,
    *,
    default: float,
    maximum: float,
) -> float:
    try:
        parsed = float(value or "")
    except ValueError:
        return default

    if parsed < 0:
        return default

    return min(parsed, maximum)


async def load_candidate_ids(
    config: RegistryJobConfig,
) -> list[int]:
    async with AsyncSessionLocal() as session:
        service = LegalEntityRegistryService(session)

        candidates = await service.list_sync_candidates(
            limit=config.batch_size,
        )

    return [
        legal_entity.id
        for legal_entity in candidates
    ]


async def sync_one_legal_entity(
    legal_entity_id: int,
    config: RegistryJobConfig,
) -> bool:
    for attempt in range(
        1,
        config.retry_attempts + 1,
    ):
        try:
            async with AsyncSessionLocal() as session:
                service = LegalEntityRegistryService(
                    session
                )

                legal_entity = (
                    await service.sync_legal_entity(
                        legal_entity_id,
                        source="scheduled_dadata",
                    )
                )

            logger.info(
                "Updated legal entity id=%s inn=%s "
                "attempt=%s",
                legal_entity.id,
                legal_entity.inn,
                attempt,
            )
            return True

        except Exception:
            logger.exception(
                "Failed to update legal entity id=%s "
                "attempt=%s/%s",
                legal_entity_id,
                attempt,
                config.retry_attempts,
            )

            if attempt < config.retry_attempts:
                await asyncio.sleep(
                    config.retry_delay_seconds
                    * attempt
                )

    return False


async def update_legal_entity_data(
    config: RegistryJobConfig | None = None,
) -> RegistryJobResult:
    effective_config = (
        config
        or RegistryJobConfig.from_environment()
    )

    result = RegistryJobResult()
    candidate_ids = await load_candidate_ids(
        effective_config
    )
    result.selected = len(candidate_ids)

    logger.info(
        "Legal entity registry update started: "
        "selected=%s batch_size=%s",
        result.selected,
        effective_config.batch_size,
    )

    for index, legal_entity_id in enumerate(
        candidate_ids
    ):
        async with AsyncSessionLocal() as session:
            entity_exists = await session.scalar(
                select(LegalEntity.id).where(
                    LegalEntity.id == legal_entity_id,
                    LegalEntity.is_active.is_(True),
                    LegalEntity.inn.is_not(None),
                )
            )

        if entity_exists is None:
            result.skipped += 1
            continue

        updated = await sync_one_legal_entity(
            legal_entity_id,
            effective_config,
        )

        if updated:
            result.updated += 1
        else:
            result.failed += 1

        if (
            index < len(candidate_ids) - 1
            and effective_config
            .request_delay_seconds
            > 0
        ):
            await asyncio.sleep(
                effective_config
                .request_delay_seconds
            )

    logger.info(
        "Legal entity registry update finished: "
        "selected=%s updated=%s failed=%s skipped=%s",
        result.selected,
        result.updated,
        result.failed,
        result.skipped,
    )

    return result


async def update_company_legal_data() -> RegistryJobResult:
    """
    Временное совместимое имя для существующего systemd-unit.

    Задача синхронизирует
    только уникальные LegalEntity.
    """

    return await update_legal_entity_data()


async def main() -> int:
    logging.basicConfig(
        level=os.getenv(
            "LOG_LEVEL",
            "INFO",
        ).upper(),
        format=(
            "%(asctime)s %(levelname)s "
            "%(name)s: %(message)s"
        ),
    )

    result = await update_legal_entity_data()

    return 0 if result.successful else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
