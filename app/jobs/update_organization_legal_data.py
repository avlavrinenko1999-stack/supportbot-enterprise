from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
import os

from app.database.db import AsyncSessionLocal
from app.services.organization_registry_service import OrganizationRegistryService


logger = logging.getLogger(__name__)


@dataclass
class OrganizationRegistryJobResult:
    selected: int = 0
    updated: int = 0
    failed: int = 0

    @property
    def successful(self) -> bool:
        return self.failed == 0


def _environment_int(name: str, default: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return min(max(value, 1), maximum)


def _environment_float(name: str, default: float, maximum: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        return default
    return min(max(value, 0), maximum)


async def update_organization_legal_data() -> OrganizationRegistryJobResult:
    batch_size = _environment_int("DADATA_ORGANIZATION_BATCH_SIZE", 100, 1000)
    retry_attempts = _environment_int("DADATA_SYNC_RETRY_ATTEMPTS", 3, 10)
    retry_delay = _environment_float("DADATA_SYNC_RETRY_DELAY_SECONDS", 5, 300)
    request_delay = _environment_float(
        "DADATA_SYNC_REQUEST_DELAY_SECONDS",
        1,
        60,
    )

    async with AsyncSessionLocal() as session:
        candidate_ids = await OrganizationRegistryService(
            session
        ).list_sync_candidate_ids(limit=batch_size)

    result = OrganizationRegistryJobResult(selected=len(candidate_ids))
    logger.info("Organization registry sync started: selected=%s", result.selected)

    for index, organization_id in enumerate(candidate_ids):
        updated = False
        for attempt in range(1, retry_attempts + 1):
            try:
                async with AsyncSessionLocal() as session:
                    await OrganizationRegistryService(
                        session
                    ).sync_organization(
                        organization_id,
                        source="scheduled_dadata",
                    )
                updated = True
                break
            except Exception:
                logger.exception(
                    "Organization registry sync failed: id=%s attempt=%s/%s",
                    organization_id,
                    attempt,
                    retry_attempts,
                )
                if attempt < retry_attempts:
                    await asyncio.sleep(retry_delay * attempt)

        if updated:
            result.updated += 1
        else:
            result.failed += 1

        if index < len(candidate_ids) - 1 and request_delay:
            await asyncio.sleep(request_delay)

    logger.info(
        "Organization registry sync finished: selected=%s updated=%s failed=%s",
        result.selected,
        result.updated,
        result.failed,
    )
    return result


async def main() -> int:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
    result = await update_organization_legal_data()
    return 0 if result.successful else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
