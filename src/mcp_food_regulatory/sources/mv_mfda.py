"""
Maldives -- Maldives Food and Drug Authority (MFDA).

Key regulations:
  Food Safety Act (Law No. 8/2019)
  Food Labelling Regulations (issued under MFDA authority)

MFDA established 2019 under the Food Safety Act. Very small island market.
Codex-aligned framework; specific health claim regulations are minimal.
Strategy: Codex-equivalent framework seeded; direct to MFDA portal.
"""

from __future__ import annotations
from mcp_food_regulatory.models import (
    Market, ClaimResult, ClaimStatus, Standard, MarketOverview, RegulatoryBasis
)
from mcp_food_regulatory.sources.base import RegulatorySource

_BASE_URL = "https://www.mfda.gov.mv"
_PARLIAMENT_URL = "https://www.parliament.gov.mv"

_KNOWN_STANDARDS: dict[str, dict] = {
    "Food Safety Act 2019": {
        "title": "Food Safety Act of Maldives (Law No. 8/2019)",
        "category": "legislation",
        "adopted": "2019",
        "summary": (
            "Establishes the Maldives Food and Drug Authority (MFDA) and the legal framework "
            "for food safety in the Maldives. Prohibits false or misleading representations "
            "on food labels including unsubstantiated health claims. "
            "Empowers MFDA to issue food labelling and claim regulations."
        ),
        "full_text_url": _PARLIAMENT_URL,
    },
    "MFDA Food Labelling Regulations": {
        "title": "Maldives Food Labelling Regulations (MFDA)",
        "category": "regulation",
        "adopted": "2020",
        "summary": (
            "Regulations issued under the Food Safety Act 2019 governing mandatory label "
            "elements and nutrition labelling for prepackaged foods sold in the Maldives. "
            "Health and nutrition claims follow Codex CAC/GL 23 principles. "
            "Very limited positive health claims list."
        ),
        "full_text_url": _BASE_URL,
    },
}

_CLAIM_PROVISIONS: dict[str, list[dict]] = {
    "vitamin c": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Codex-aligned (MFDA Food Labelling Regulations): "
                "'Source of Vitamin C' -- at least 15% RDI per 100g/100ml or per serving. "
                "'High in Vitamin C' -- at least 30% RDI. "
                "Claims must be truthful and not misleading per Food Safety Act 2019."
            ),
            "instrument": "MFDA Food Labelling Regulations (Codex CAC/GL 23-aligned)",
            "url": _BASE_URL,
            "last_updated": "2020",
        }
    ],
    "calcium": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Codex-aligned: 'Source of Calcium' -- at least 15% RDI per 100g/100ml. "
                "Health claims beyond nutrient content require MFDA review."
            ),
            "instrument": "MFDA Food Labelling Regulations",
            "url": _BASE_URL,
            "last_updated": "2020",
        }
    ],
    "dietary fibre": [
        {
            "claim_type": "nutrition_claim",
            "status": "permitted",
            "conditions": (
                "Codex-aligned: 'Source of Dietary Fibre' -- at least 3g/100g or 1.5g/100kcal. "
                "'High in Dietary Fibre' -- at least 6g/100g."
            ),
            "instrument": "MFDA Food Labelling Regulations",
            "url": _BASE_URL,
            "last_updated": "2020",
        }
    ],
}


class MVMFDASource(RegulatorySource):
    """MFDA data source for Maldives."""

    market = Market.MV
    BASE_URL = _BASE_URL

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
                    market=Market.MV,
                    ingredient=ingredient,
                    claim_type=p["claim_type"],
                    status=ClaimStatus(p["status"]),
                    conditions=p.get("conditions"),
                    basis=RegulatoryBasis(
                        instrument=p["instrument"],
                        url=p.get("url"),
                        notes="Maldives follows Codex CAC/GL 23 principles. Very small market; MFDA established 2019. Minimal published health-claim regulations.",
                    ),
                    last_updated=p.get("last_updated"),
                    source_url=p.get("url"),
                ))

        if not results:
            results.append(ClaimResult(
                market=Market.MV,
                ingredient=ingredient,
                claim_type=claim_type or "health_claim",
                status=ClaimStatus.NOT_DEFINED,
                conditions=(
                    f"No pre-indexed MFDA claim data for '{ingredient}'. "
                    "Maldives follows Codex CAC/GL 23 principles under the Food Safety Act 2019. "
                    "Contact MFDA (mfda.gov.mv) directly. Very small market with minimal "
                    "published health-claim-specific regulations."
                ),
                basis=RegulatoryBasis(
                    instrument="Food Safety Act 2019 + MFDA Food Labelling Regulations",
                    url=_BASE_URL,
                    notes="Very limited online regulatory data for health claims. Codex-aligned framework.",
                ),
                source_url=_BASE_URL,
            ))

        return results

    async def get_standard(self, standard_id: str) -> Standard | None:
        upper = standard_id.upper()
        for key, data in _KNOWN_STANDARDS.items():
            if upper in key.upper() or key.upper() in upper:
                return Standard(standard_id=key, market=Market.MV, **data)
        return None

    async def search_standards(self, query: str) -> list[Standard]:
        q = query.lower()
        return [
            Standard(standard_id=k, market=Market.MV, **v)
            for k, v in _KNOWN_STANDARDS.items()
            if q in k.lower() or q in v["title"].lower() or q in (v.get("summary") or "").lower()
        ] or [Standard(standard_id=k, market=Market.MV, **v) for k, v in _KNOWN_STANDARDS.items()]

    async def get_market_overview(self) -> MarketOverview:
        return MarketOverview(
            market=Market.MV,
            authority_name="Maldives Food and Drug Authority (MFDA)",
            authority_url=_BASE_URL,
            key_legislation=[
                "Food Safety Act of Maldives (Law No. 8/2019)",
                "MFDA Food Labelling Regulations",
            ],
            health_claims_framework=(
                "The Maldives regulates health claims under the Food Safety Act 2019 (Law No. 8/2019). "
                "MFDA (established 2019) follows Codex CAC/GL 23 principles for nutrition and health claims. "
                "Very small island nation market; health-claim-specific regulations are minimal. "
                "Claims must be truthful and not misleading. "
                "No published positive health claims list; non-trivial claims require MFDA review."
            ),
            notes=(
                f"MFDA: {_BASE_URL} | "
                f"Parliament of Maldives (laws): {_PARLIAMENT_URL}"
            ),
        )
