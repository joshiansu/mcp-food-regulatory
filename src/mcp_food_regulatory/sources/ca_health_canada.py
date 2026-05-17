"""
Health Canada / CFIA regulatory data source for Canada.

Two types of pre-approved health claims:
  1. Disease Risk Reduction Claims (DRRC) -- FDR B.01.603
     Status: PERMITTED
  2. Nutrient Function Claims (NFC) -- FDR B.01.500-B.01.513
     Status: PERMITTED

Both published as structured HTML pages on canada.ca.

Implementation:
  search_health_claims() -- Fetches both claims pages (cached 24h).
  get_standard()         -- Seeded for key regulations.
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

_BASE_URL = "https://www.canada.ca"
_DRRC_URL = (
    "https://www.canada.ca/en/health-canada/services/food-nutrition/"
    "food-labelling/health-claims/diet-related-health-claims.html"
)
_NFC_URL = (
    "https://www.canada.ca/en/health-canada/services/food-nutrition/"
    "food-labelling/health-claims/nutrient-function-claims.html"
)
_CACHE_TTL = 86400

_drrc_cache: list[dict] | None = None
_drrc_fetched_at: float = 0.0
_nfc_cache: list[dict] | None = None
_nfc_fetched_at: float = 0.0

_KNOWN_STANDARDS: dict[str, dict] = {
    "FDR B.01.603": {
        "title": "Food and Drug Regulations B.01.603 -- Disease Risk Reduction Claims",
        "category": "regulation",
        "adopted": "2003",
        "last_amended": "2016",
        "summary": (
            "Authorizes specific diet-disease risk reduction claims on Canadian food labels. "
            "Claims must use prescribed wording. Covers: sodium/hypertension, "
            "saturated fat/cholesterol/heart disease, calcium/osteoporosis, "
            "vegetables and fruit/cancer, sugar alcohols/dental caries."
        ),
        "full_text_url": "https://laws-lois.justice.gc.ca/eng/regulations/C.R.C.,_c._870/page-63.html",
    },
    "FDR B.01.500": {
        "title": "Food and Drug Regulations B.01.500-B.01.513 -- Nutrient Function Claims",
        "category": "regulation",
        "adopted": "2003",
        "summary": (
            "Pre-approved list of nutrient function claims for vitamins and minerals. "
            "Claims state the role of the nutrient in maintaining good health. "
            "No individual pre-market approval required."
        ),
        "full_text_url": "https://laws-lois.justice.gc.ca/eng/regulations/C.R.C.,_c._870/page-62.html",
    },
    "Food and Drugs Act": {
        "title": "Food and Drugs Act (R.S.C., 1985, c. F-27)",
        "category": "legislation",
        "adopted": "1985",
        "last_amended": "2022",
        "summary": "Foundational Canadian legislation governing food safety, labeling, and health claims.",
        "full_text_url": "https://laws-lois.justice.gc.ca/eng/acts/f-27/",
    },
}


class CAHealthCanadaSource(RegulatorySource):
    """
    Health Canada data source for Canada.

    Disease Risk Reduction Claims and Nutrient Function Claims
    fetched live from canada.ca (cached 24h).
    """

    market = Market.CA
    BASE_URL = _BASE_URL

    async def search_health_claims(
        self,
        ingredient: str,
        claim_type: str | None = None,
    ) -> list[ClaimResult]:
        normalized = ingredient.lower().strip()
        results = []

        # Disease Risk Reduction Claims -> PERMITTED
        if claim_type is None or claim_type in ("disease_risk_reduction", "health_claim"):
            try:
                for item in await self._get_drrc():
                    if normalized in item["text"].lower():
                        results.append(ClaimResult(
                            market=Market.CA,
                            ingredient=ingredient,
                            claim_type="disease_risk_reduction",
                            status=ClaimStatus.PERMITTED,
                            conditions=item["text"],
                            basis=RegulatoryBasis(
                                instrument="FDR B.01.603",
                                article=None,
                                url=_DRRC_URL,
                                notes="Pre-approved Disease Risk Reduction Claim. Must use prescribed wording.",
                            ),
                            source_url=_DRRC_URL,
                        ))
            except Exception:
                pass

        # Nutrient Function Claims -> PERMITTED
        if claim_type is None or claim_type in ("nutrient_function", "health_claim"):
            try:
                for item in await self._get_nfc():
                    if normalized in item["text"].lower():
                        results.append(ClaimResult(
                            market=Market.CA,
                            ingredient=ingredient,
                            claim_type="nutrient_function",
                            status=ClaimStatus.PERMITTED,
                            conditions=item["text"],
                            basis=RegulatoryBasis(
                                instrument="FDR B.01.500-B.01.513",
                                article=None,
                                url=_NFC_URL,
                                notes="Pre-approved Nutrient Function Claim. No individual pre-market approval required.",
                            ),
                            source_url=_NFC_URL,
                        ))
            except Exception:
                pass

        if not results:
            results.append(ClaimResult(
                market=Market.CA,
                ingredient=ingredient,
                claim_type=claim_type or "health_claim",
                status=ClaimStatus.NOT_DEFINED,
                conditions=None,
                basis=RegulatoryBasis(
                    instrument="Food and Drug Regulations",
                    article=None,
                    url=_BASE_URL + "/en/health-canada/services/food-nutrition/food-labelling/health-claims.html",
                    notes="No pre-approved health claim found for this ingredient under Canadian food regulations.",
                ),
                source_url=_BASE_URL,
            ))

        return results

    async def _get_drrc(self) -> list[dict]:
        global _drrc_cache, _drrc_fetched_at
        if _drrc_cache is None or (time.time() - _drrc_fetched_at) > _CACHE_TTL:
            _drrc_cache = await self._fetch_claims_page(_DRRC_URL)
            _drrc_fetched_at = time.time()
        return _drrc_cache

    async def _get_nfc(self) -> list[dict]:
        global _nfc_cache, _nfc_fetched_at
        if _nfc_cache is None or (time.time() - _nfc_fetched_at) > _CACHE_TTL:
            _nfc_cache = await self._fetch_claims_page(_NFC_URL)
            _nfc_fetched_at = time.time()
        return _nfc_cache

    async def _fetch_claims_page(self, url: str) -> list[dict]:
        resp = await self._get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        items = []
        for tag in soup.find_all(["li", "td", "p"]):
            text = tag.get_text(strip=True)
            if len(text) > 30:
                items.append({"text": text})
        return items

    async def get_standard(self, standard_id: str) -> Standard | None:
        upper = standard_id.upper()
        for key, data in _KNOWN_STANDARDS.items():
            if upper in key.upper() or key.upper() in upper:
                return Standard(standard_id=key, market=Market.CA, **data)
        return None

    async def search_standards(self, query: str) -> list[Standard]:
        query_lower = query.lower()
        results = [
            Standard(standard_id=key, market=Market.CA, **data)
            for key, data in _KNOWN_STANDARDS.items()
            if query_lower in key.lower()
            or query_lower in data["title"].lower()
            or query_lower in (data.get("summary") or "").lower()
        ]
        return results or [
            Standard(standard_id=k, market=Market.CA, **v)
            for k, v in _KNOWN_STANDARDS.items()
        ]

    async def get_market_overview(self) -> MarketOverview:
        return MarketOverview(
            market=Market.CA,
            authority_name="Health Canada / Canadian Food Inspection Agency (CFIA)",
            authority_url=_BASE_URL,
            key_legislation=[
                "Food and Drugs Act (R.S.C. 1985, c. F-27)",
                "Food and Drug Regulations -- B.01.603 (Disease Risk Reduction Claims)",
                "Food and Drug Regulations -- B.01.500-B.01.513 (Nutrient Function Claims)",
                "Safe Food for Canadians Regulations (SFCR) 2019",
            ],
            health_claims_framework=(
                "Canada permits two types of pre-approved health claims: "
                "Disease Risk Reduction Claims (DRRC, FDR B.01.603) linking diet to reduced disease risk, "
                "and Nutrient Function Claims (NFC, FDR B.01.500-513) describing nutrient roles in the body. "
                "Both require prescribed wording. Novel health claims require Health Canada pre-approval."
            ),
        )
