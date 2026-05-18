"""
Saudi Arabia -- Saudi Food and Drug Authority (SFDA).

Key regulations:
  SFDA.FD 9001:2017 -- Food Labelling Technical Regulation
  SFDA Technical Regulation on Health Claims (bilingual Arabic/English)
  GCC/GSO standards -- Saudi Arabia adopts GCC Standardisation Organisation
  standards, which largely align with Codex.

SFDA publishes bilingual (Arabic/English) regulations as PDFs.
The SFDA portal (sfda.gov.sa) has a searchable document library.
Most structured of the Gulf states for regulatory data access.
"""

from __future__ import annotations
from mcp_food_regulatory.models import (
    Market, ClaimResult, ClaimStatus, Standard, MarketOverview, RegulatoryBasis
)
from mcp_food_regulatory.sources.base import RegulatorySource

_BASE_URL = "https://www.sfda.gov.sa/en/food"
_SFDA_URL = "https://www.sfda.gov.sa"
_GSO_URL = "https://www.gso.org.sa"

_KNOWN_STANDARDS: dict[str, dict] = {
    "SFDA.FD 9001:2017": {
        "title": "SFDA Food Labelling Technical Regulation (SFDA.FD 9001:2017)",
        "category": "technical_regulation",
        "adopted": "2017",
        "summary": (
            "Primary labelling regulation for packaged foods in Saudi Arabia. "
            "Covers mandatory label declarations, language requirements (Arabic), "
            "nutrition labelling, and claim restrictions. "
            "Bilingual (Arabic/English) official text available on SFDA portal."
        ),
        "full_text_url": "https://www.sfda.gov.sa/en/food/regulations",
    },
    "GSO CAC/GL 23": {
        "title": "GCC Standard GSO CAC/GL 23 -- Guidelines for Use of Nutrition and Health Claims",
        "category": "regional_standard",
        "adopted": "2013",
        "summary": (
            "GCC adoption of Codex CAC/GL 23-1997 (Guidelines on Nutrition and Health Claims). "
            "Defines conditions for nutrition claims and health claims across GCC states "
            "including Saudi Arabia, UAE, Kuwait, Bahrain, Oman, and Qatar."
        ),
        "full_text_url": _GSO_URL,
    },
    "GSO 9:2013": {
        "title": "GCC Standard GSO 9:2013 -- Nutrition Labelling of Prepackaged Foods",
        "category": "regional_standard",
        "adopted": "2013",
        "summary": (
            "GCC regional standard for nutrition labelling, harmonised across Saudi Arabia "
            "and GCC member states. Defines reference daily intakes (RDIs) used as the "
            "basis for nutrient content claims in the GCC region."
        ),
        "full_text_url": _GSO_URL,
    },
}

_CLAIM_PROVISIONS: dict[str, list[dict]] = {
    "vitamin c": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "GSO CAC/GL 23 / SFDA: 'Source of Vitamin C' -- at least 15% RDI per 100g/100ml "
                "or per serving. 'High in Vitamin C' -- at least 30% RDI. "
                "GCC RDI for Vitamin C: 75 mg/day (adult). "
                "Label must be in Arabic; English may also be included."
            ),
            "instrument": "GSO CAC/GL 23 + SFDA.FD 9001:2017",
            "url": _BASE_URL,
            "last_updated": "2017",
        }
    ],
    "vitamin d": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "GSO CAC/GL 23 / SFDA: 'Source of Vitamin D' -- at least 15% RDI per 100g/100ml. "
                "GCC RDI for Vitamin D: 5 µg/day (200 IU). "
                "Health claims linking Vitamin D to bone health must be substantiated and "
                "are subject to SFDA review."
            ),
            "instrument": "GSO CAC/GL 23 + SFDA.FD 9001:2017",
            "url": _BASE_URL,
            "last_updated": "2017",
        }
    ],
    "calcium": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "GSO CAC/GL 23: 'Source of Calcium' -- at least 15% RDI per 100g/100ml. "
                "'High in Calcium' -- at least 30% RDI. GCC RDI for Calcium: 800 mg/day. "
                "Health claim linking calcium to bone health is conditionally permitted "
                "under Codex-aligned GSO guidelines."
            ),
            "instrument": "GSO CAC/GL 23 + SFDA.FD 9001:2017",
            "url": _BASE_URL,
            "last_updated": "2017",
        }
    ],
    "dietary fibre": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "GSO CAC/GL 23: 'Source of Dietary Fibre' -- at least 3g/100g or 1.5g/100kcal. "
                "'High in Dietary Fibre' -- at least 6g/100g or 3g/100kcal. "
                "Aligned with Codex CAC/GL 23-1997 conditions."
            ),
            "instrument": "GSO CAC/GL 23",
            "url": _GSO_URL,
            "last_updated": "2013",
        }
    ],
    "omega-3": [
        {
            "claim_type": "nutrition_claim",
            "status": "conditional",
            "conditions": (
                "GSO CAC/GL 23 includes omega-3 nutrition claim conditions aligned with Codex. "
                "'Source of Omega-3' -- at least 0.3g ALA per 100g or 40mg EPA+DHA per 100g. "
                "Cardiovascular health claims require SFDA substantiation review. "
                "Refer to SFDA Technical Regulation on Health Claims for current approved list."
            ),
            "instrument": "GSO CAC/GL 23 + SFDA Health Claims Regulation",
            "url": _BASE_URL,
            "last_updated": "2017",
        }
    ],
}


class SASFDASource(RegulatorySource):
    """SFDA data source for Saudi Arabia."""

    market = Market.SA
    BASE_URL = _SFDA_URL

    async def search_health_claims(
        self,
        ingredient: str,
        claim_type: str | None = None,
    ) -> list[ClaimResult]:
        normalized = ingredient.lower().strip()
        results: list[ClaimResult] = []

        provisions = _CLAIM_PROVISIONS.get(normalized, [])
        for p in provisions:
            if claim_type is None or claim_type.lower() in p["claim_type"].lower():
                results.append(ClaimResult(
                    market=Market.SA,
                    ingredient=ingredient,
                    claim_type=p["claim_type"],
                    status=ClaimStatus(p["status"]),
                    conditions=p.get("conditions"),
                    basis=RegulatoryBasis(
                        instrument=p["instrument"],
                        url=p.get("url"),
                        notes="Saudi Arabia adopts GCC/GSO standards aligned with Codex. SFDA publishes bilingual (Arabic/English) regulations.",
                    ),
                    last_updated=p.get("last_updated"),
                    source_url=p.get("url"),
                ))

        if not results:
            results.append(ClaimResult(
                market=Market.SA,
                ingredient=ingredient,
                claim_type=claim_type or "health_claim",
                status=ClaimStatus.NOT_DEFINED,
                conditions=(
                    f"No pre-indexed SFDA claim data for '{ingredient}'. "
                    "Check SFDA portal (sfda.gov.sa) food regulations section or "
                    "GSO standards database for applicable GCC-wide nutrition claim conditions."
                ),
                basis=RegulatoryBasis(
                    instrument="SFDA.FD 9001:2017 + GSO CAC/GL 23",
                    url=_BASE_URL,
                    notes="SFDA is among the most structured Gulf authorities; bilingual regulations available.",
                ),
                source_url=_BASE_URL,
            ))

        return results

    async def get_standard(self, standard_id: str) -> Standard | None:
        upper = standard_id.upper()
        for key, data in _KNOWN_STANDARDS.items():
            if upper in key.upper() or key.upper() in upper:
                return Standard(standard_id=key, market=Market.SA, **data)
        return None

    async def search_standards(self, query: str) -> list[Standard]:
        q = query.lower()
        return [
            Standard(standard_id=k, market=Market.SA, **v)
            for k, v in _KNOWN_STANDARDS.items()
            if q in k.lower() or q in v["title"].lower() or q in (v.get("summary") or "").lower()
        ] or [Standard(standard_id=k, market=Market.SA, **v) for k, v in _KNOWN_STANDARDS.items()]

    async def get_market_overview(self) -> MarketOverview:
        return MarketOverview(
            market=Market.SA,
            authority_name="Saudi Food and Drug Authority (SFDA / هيئة الغذاء والدواء)",
            authority_url=_SFDA_URL,
            key_legislation=[
                "SFDA.FD 9001:2017 -- Food Labelling Technical Regulation",
                "GSO CAC/GL 23 -- GCC Guidelines for Nutrition and Health Claims",
                "GSO 9:2013 -- GCC Nutrition Labelling Standard",
                "Saudi Food and Drug Authority Law (Royal Decree M/35, 2003)",
            ],
            health_claims_framework=(
                "Saudi Arabia regulates health claims through SFDA, aligned with GCC/GSO "
                "standards which adopt Codex CAC/GL 23-1997. Nutrition claims must meet "
                "GSO 9:2013 thresholds. Health claims must be scientifically substantiated "
                "and are subject to SFDA review. Labels must be in Arabic; English may be "
                "included additionally. SFDA publishes regulations in Arabic and English."
            ),
            notes=(
                f"Most structured of Gulf states for regulatory access. "
                f"SFDA portal: {_SFDA_URL} | GSO standards: {_GSO_URL}"
            ),
        )
