from __future__ import annotations

import os
from datetime import datetime, timezone

import httpx

from app.integrations.dadata.models import DadataCompany


class DadataClient:
    API_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party"

    STATUS_LABELS = {
        "ACTIVE": "✅ Действующая",
        "LIQUIDATING": "⚠️ Ликвидируется",
        "LIQUIDATED": "⛔ Ликвидирована",
        "BANKRUPT": "🚫 Банкротство",
        "REORGANIZING": "🔄 Реорганизация",
    }

    def __init__(self, token: str | None = None):
        self.token = token or os.getenv("DADATA_API_TOKEN")

    @staticmethod
    def _format_timestamp(value) -> str | None:
        if value in (None, ""):
            return None

        try:
            seconds = int(value) / 1000
            return datetime.fromtimestamp(seconds, tz=timezone.utc).date().isoformat()
        except (TypeError, ValueError, OSError):
            return None

    async def find_company_by_inn(self, inn: str) -> DadataCompany:
        clean_inn = "".join(ch for ch in inn if ch.isdigit())

        if len(clean_inn) not in (10, 12):
            raise ValueError("ИНН должен содержать 10 или 12 цифр.")

        if not self.token:
            raise ValueError("Не задан DADATA_API_TOKEN в .env.")

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                self.API_URL,
                headers={
                    "Authorization": f"Token {self.token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={"query": clean_inn, "count": 1},
            )

        if response.status_code != 200:
            raise ValueError(f"DaData вернула ошибку: HTTP {response.status_code}")

        payload = response.json()
        suggestions = payload.get("suggestions") or []

        if not suggestions:
            raise ValueError("Компания по этому ИНН не найдена.")

        suggestion = suggestions[0]
        data = suggestion.get("data") or {}
        name = data.get("name") or {}
        address = data.get("address") or {}
        state = data.get("state") or {}

        short_name = (
            name.get("short_with_opf")
            or name.get("short")
            or suggestion.get("value")
        )
        full_name = name.get("full_with_opf") or name.get("full")

        status_code = state.get("status")
        status_label = self.STATUS_LABELS.get(status_code, status_code)

        return DadataCompany(
            inn=data.get("inn") or clean_inn,
            kpp=data.get("kpp"),
            ogrn=data.get("ogrn"),
            name=short_name or full_name or clean_inn,
            legal_name=full_name,
            legal_address=address.get("unrestricted_value") or address.get("value"),
            legal_status=status_label,
            legal_status_code=status_code,
            registration_date=self._format_timestamp(state.get("registration_date")),
            liquidation_date=self._format_timestamp(state.get("liquidation_date")),
        )
