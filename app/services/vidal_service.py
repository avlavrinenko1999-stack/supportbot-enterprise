import html
import re
import time
from dataclasses import dataclass
from urllib.parse import quote

import aiohttp


VIDAL_BASE_URL = "https://www.vidal.ru"


@dataclass(frozen=True, slots=True)
class VidalSearchResult:
    name: str
    url: str
    release_form: str
    registration: str
    company: str
    availability: str


class VidalService:
    _cache: dict[str, tuple[float, list[VidalSearchResult]]] = {}
    CACHE_TTL_SECONDS = 300
    MAX_RESULTS = 20

    @classmethod
    async def search(cls, query: str) -> list[VidalSearchResult]:
        clean_query = " ".join(query.split())
        if len(clean_query) < 2:
            return []
        cache_key = clean_query.casefold()
        cached = cls._cache.get(cache_key)
        if cached and time.monotonic() - cached[0] < cls.CACHE_TTL_SECONDS:
            return cached[1]
        url = f"{VIDAL_BASE_URL}/drugs?t=product&q={quote(clean_query)}"
        timeout = aiohttp.ClientTimeout(total=20, connect=8)
        headers = {
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": "SupportBot-Enterprise-Vidal-Gateway/1.0",
        }
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as client:
            async with client.get(url, allow_redirects=True) as response:
                response.raise_for_status()
                body = await response.text()
        results = cls.parse_search_results(body)
        cls._cache[cache_key] = (time.monotonic(), results)
        return results

    @classmethod
    def parse_search_results(cls, body: str) -> list[VidalSearchResult]:
        results = []
        for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>', body, flags=re.I | re.S):
            name_cell = cls._cell(row, "products-table-name")
            form_cell = cls._cell(row, "products-table-zip")
            company_cell = cls._cell(row, "products-table-company")
            if not name_cell or not form_cell:
                continue
            link = re.search(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', name_cell, flags=re.I | re.S)
            if not link or not link.group(1).startswith("/drugs/"):
                continue
            name = cls._text(link.group(2))
            if not name:
                continue
            release_form_match = re.search(r'<div\b[^>]*class="[^"]*hyphenate[^"]*"[^>]*>(.*?)</div>', form_cell, flags=re.I | re.S)
            release_form = cls._text(release_form_match.group(1)) if release_form_match else ""
            form_text = cls._text(form_cell)
            registration = form_text[len(release_form):].strip(" ·") if release_form and form_text.startswith(release_form) else form_text
            availability_match = re.search(r'alt="([^"]+)"', row, flags=re.I)
            results.append(
                VidalSearchResult(
                    name=name,
                    url=f"{VIDAL_BASE_URL}{link.group(1)}",
                    release_form=release_form,
                    registration=registration,
                    company=cls._text(company_cell),
                    availability=html.unescape(availability_match.group(1)).strip() if availability_match else "",
                )
            )
            if len(results) >= cls.MAX_RESULTS:
                break
        return results

    @staticmethod
    def _cell(row: str, class_name: str) -> str:
        match = re.search(
            rf'<td\b[^>]*class="[^"]*{re.escape(class_name)}[^"]*"[^>]*>(.*?)</td>',
            row,
            flags=re.I | re.S,
        )
        return match.group(1) if match else ""

    @staticmethod
    def _text(fragment: str) -> str:
        without_tags = re.sub(r"<[^>]+>", " ", fragment)
        return " ".join(html.unescape(without_tags).split())
