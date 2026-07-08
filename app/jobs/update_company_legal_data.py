import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.integrations.dadata import DadataClient
from app.models.company import Company

load_dotenv()

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "company_legal_update.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


async def update_companies() -> None:
    client = DadataClient()

    async with AsyncSessionLocal() as session:
        companies = list(
            await session.scalars(
                select(Company)
                .where(Company.inn.is_not(None))
                .order_by(Company.id)
            )
        )

        logging.info("Started company legal update. Companies with INN: %s", len(companies))

        updated = 0
        failed = 0

        for company in companies:
            try:
                data = await client.find_company_by_inn(company.inn or "")

                company.name = data.name
                company.inn = data.inn
                company.kpp = data.kpp
                company.ogrn = data.ogrn
                company.legal_name = data.legal_name
                company.legal_address = data.legal_address
                company.legal_status = data.legal_status
                company.legal_status_code = data.legal_status_code
                company.registration_date = data.registration_date
                company.liquidation_date = data.liquidation_date
                company.last_registry_sync_at = datetime.now(timezone.utc)

                await session.commit()
                updated += 1

                logging.info("Updated company id=%s inn=%s", company.id, company.inn)

                await asyncio.sleep(0.3)

            except Exception as error:
                await session.rollback()
                failed += 1
                logging.exception(
                    "Failed to update company id=%s inn=%s: %s",
                    company.id,
                    company.inn,
                    error,
                )

        logging.info(
            "Finished company legal update. Updated=%s Failed=%s",
            updated,
            failed,
        )


if __name__ == "__main__":
    asyncio.run(update_companies())
