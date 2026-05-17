"""
Food Standards Australia New Zealand (FSANZ) regulatory data source.

Health claims governed by Standard 1.2.7 of the Australia New Zealand Food Standards Code:
  - General level health claims (Schedule 3): CONDITIONAL
    (food must pass nutrient profiling score per clause 17)
  - High level health claims (Schedule 4): PERMITTED
    (pre-approved list referencing serious disease/conditions)

Implementation:
  search_health_claims() -- Fetches Standard 1.2.7 from legislation.gov.au (cached 24h).
  get_standard()         -- Seeded for key standards.
  search_standards()     -- Seeded list.
  get_market_overview()  -- Static.
"""

from __future__ import annotations
import time
from bs4 import BeautifulSoup
from mcp_food_regulatory.models import (
    Market, ClaimResult, ClaimStatus, Standard, MarketOverview, RegulatoryBasis
)
from mcp_food_regulatory.sources.base import RegulatorySource

_BASE_URL = "https://www.foodstandards.gov.au"
_STD127_URL = "https://www.legislation.gov.au/Series/F2015L00411"
_CACHE_TTL = 86400

_std127_cache: list[dict] | None = None
_std127_fetched_at: float = 0.0

_KNOWN_STANDARDS: dict[str, dict] = {
    "Standard 1.2.7": {
        "title": (
            "Australia New Zealand Food Standards Code -- "
            "Standard 1.2.7 -- Nutrition, Health and Related Claims"
        ),
        "category": "standard",
        "adopted": "2013",
        "last_amended": "2022",
        "summary": (
            "Governs nutrition content claims and health claims in Australia and New Zealand. "
            "Schedule 2: Conditions for nutrition content claims. "
            "Schedule 3: Pre-approved general level health claims (food-health relationships). "
            "Schedule 4: Pre-approved high level health claims (refer to serious disease/conditions)."
        ),
        "full_text_url": _STD127_URL,
        "key_definitions": {
            "General level health claim": (
                "A health claim that does not refer to a serious disease or condition."
            ),
            "High level health claim": (
                "A health claim that refers to a serious disease or biomarker of a serious disease."
            ),
            "Nutrient profiling score": (
                "A score calculated per Standard 1.2.7 clause 17. "
                "Food must achieve a passing score to carry general level health claims."
            ),
        },
    },
    "Standard 1.2.8": {
        "title": (
            "Australia New Zealand Food Standards Code -- "
            "Standard 1.2.8 -- Nutrition Information Requirements"
        ),
        "category": "standard",
        "adopted": "2013",
        "summary": "Mandates the Nutrition Information Panel (NIP) format for Australian and NZ packaged foods.",
        "full_text_url": "https://www.legislation.gov.au/Series/F2015L00410",
    },
    "FSANZ Act 1991": {
        "title": "Food Standards Australia New Zealand Act 1991",
        "category": "legislation",
        "adopted": "1991",
        "last_amended": "2020",
        "summary": (
            "Establishes FSANZ and its mandate to develop and administer "
            "the Australia New Zealand Food Standards Code."
        ),
        "full_text_url": "https://www.legislation.gov.au/Series/C2004A04182",
    },
}


class AUFSANZSource(RegulatorySource):
    """
    FSANZ data source for Australia (and New Zealand).

    Standard 1.2.7 fetched from legislation.gov.au (cached 24h).
    Schedule 4 (high level) -> PERMITTED.
    Schedule 3 (general level) -> CONDITIONAL (nutrient profiling score required).
    """

    market = Market.AU
    BASE_URL = _BASE_URL

    async def search_health_claims(
        self,
        ingredient: str,
        claim_type: str | None = None,
    ) -> list[ClaimResult]:
        normalized = ingredient.lower().strip()
        results = []

        try:
            for item in await self._get_std127_data():
                if normalized in item["text"].lower():
                    is_high = item["schedule"] == "4"
                    status = ClaimStatus.PERMITTED if is_high else ClaimStatus.CONDITIONAL
                    claim_t = (
                        "high_level_health_claim" if is_high
                        else "general_level_health_claim"
                    )
                    if claim_type is None or claim_type == claim_t:
                        conditions = item["text"]
                        if not is_high:
                            conditions += (
                                " Food must achieve a passing nutrient profiling score "
                                "per Standard 1.2.7 clause 17 before this claim may be used."
                            )
                        results.append(ClaimResult(
                            market=Market.AU,
                            ingredient=ingredient,
                            claim_type=claim_t,
                            status=status,
                            conditions=conditions,
                            basis=RegulatoryBasis(
                                instrument="Standard 1.2.7",
                                article=f"Schedule {item['schedule']}",
                                url=_STD127_URL,
                                notes=(
                                    f"Pre-approved food-health relationship from "
                                    f"Schedule {item['schedule']} of Standard 1.2.7."
                                ),
                            ),
                            source_url=_STD127_URL,
                        ))
        except Exception:
            pass

        if not results:
            results.append(ClaimResult(
                market=Market.AU,
                ingredient=ingredient,
                claim_type=claim_type or "health_claim",
                status=ClaimStatus.NOT_DEFINED,
                conditions=None,
                basis=RegulatoryBasis(
                    instrument="Standard 1.2.7",
                    article=None,
                    url=_STD127_URL,
                    notes=(
                        "No pre-approved health claim found in Standard 1.2.7 for this ingredient. "
                        "Self-substantiated general level health claims may be possible with adequate evidence."
                    ),
                ),
                source_url=_BASE_URL,
            ))

        return results

    async def _get_std127_data(self) -> list[dict]:
        global _std127_cache, _std127_fetched_at
        if _std127_cache is None or (time.time() - _std127_fetched_at) > _CACHE_TTL:
            _std127_cache = await self._fetch_std127()
            _std127_fetched_at = time.time()
        return _std127_cache

    async def _fetch_std127(self) -> list[dict]:
        resp = await self._get(_STD127_URL)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        items = []
        current_schedule = "3"
        for tag in soup.find_all(["h2", "h3", "h4", "td", "li", "p"]):
            text = tag.get_text(strip=True)
            if "schedule 4" in text.lower():
                current_schedule = "4"
            elif "schedule 3" in text.lower():
                current_schedule = "3"
            if len(text) > 30 and tag.name in ("td", "li", "p"):
                items.append({"text": text, "schedule": current_schedule})
        return items

    async def get_standard(self, standard_id: str) -> Standard | None:
        upper = standard_id.upper()
        for key, data in _KNOWN_STANDARDS.items():
            if upper in key.upper() or key.upper() in upper:
                return Standard(standard_id=key, market=Market.AU, **data)
        return None

    async def search_standards(self, query: str) -> list[Standard]:
        query_lower = query.lower()
        results = [
            Standard(standard_id=key, market=Market.AU, **data)
            for key, data in _KNOWN_STANDARDS.items()
            if query_lower in key.lower()
            or query_lower in data["title"].lower()
            or query_lower in (data.get("summary") or "").lower()
        ]
        return results or [
            Standard(standard_id=k, market=Market.AU, **v)
            for k, v in _KNOWN_STANDARDS.items()
        ]

    async def get_market_overview(self) -> MarketOverview:
        return MarketOverview(
            market=Market.AU,
            authority_name="Food Standards Australia New Zealand (FSANZ)",
            authority_url=_BASE_URL,
            key_legislation=[
                "Food Standards Australia New Zealand Act 1991",
                "Standard 1.2.7 -- Nutrition, Health and Related Claims",
                "Standard 1.2.8 -- Nutrition Information Requirements",
            ],
            health_claims_framework=(
                "Health claims in Australia and New Zealand are governed by Standard 1.2.7. "
                "General level health claims (Schedule 3) are CONDITIONAL -- "
                "food must pass nutrient profiling score per clause 17. "
                "High level health claims (Schedule 4) are PERMITTED from a pre-approved list. "
                "Self-substantiated general level claims are also permitted with adequate evidence."
            ),
            notes=(
                "Standard 1.2.7 applies in both Australia and New Zealand. "
                "FSANZ develops the standards; state/territory food enforcement authorities administer them. "
                "NZ has some additional provisions -- check FSANZ Application A1090."
            ),
        )
