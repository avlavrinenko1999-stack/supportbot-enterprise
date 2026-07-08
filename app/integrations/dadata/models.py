from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DadataCompany:
    inn: str
    kpp: str | None
    ogrn: str | None
    name: str
    legal_name: str | None
    legal_address: str | None
    legal_status: str | None
    legal_status_code: str | None
    registration_date: str | None
    liquidation_date: str | None
